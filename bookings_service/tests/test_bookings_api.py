import os
os.environ["TESTING"] = "1"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from app.main import app
from app.database import Base, get_db
from app.auth import TokenData

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_bookings.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def create_mock_token_data(role="regular", user_id=1, username="testuser"):
    """Helper to create mock token data for auth bypass"""
    return TokenData(username=username, user_id=user_id, role=role)


@pytest.fixture
def mock_admin():
    """Mock admin authentication"""
    from app.deps import get_current_token_data
    app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="admin", user_id=100)
    yield
    app.dependency_overrides.pop(get_current_token_data, None)


@pytest.fixture
def mock_regular_user():
    """Mock regular user authentication"""
    from app.deps import get_current_token_data
    app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="regular", user_id=1)
    yield
    app.dependency_overrides.pop(get_current_token_data, None)


@pytest.fixture
def mock_another_user():
    """Mock another regular user authentication"""
    from app.deps import get_current_token_data
    app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="regular", user_id=2, username="another_user")
    yield
    app.dependency_overrides.pop(get_current_token_data, None)


@pytest.fixture
def mock_auditor():
    """Mock auditor authentication"""
    from app.deps import get_current_token_data
    app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="auditor", user_id=200)
    yield
    app.dependency_overrides.pop(get_current_token_data, None)


def get_future_datetime(hours_from_now=1):
    """Get a datetime in the future"""
    return datetime.utcnow() + timedelta(hours=hours_from_now)


class TestBookingCreation:
    """Test booking creation endpoints"""
    
    def test_create_booking_success(self, mock_regular_user):
        start = get_future_datetime(1)
        end = get_future_datetime(2)
        
        response = client.post(
            "/bookings/",
            json={
                "room_id": 1,
                "start_time": start.isoformat(),
                "end_time": end.isoformat()
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["room_id"] == 1
        assert data["user_id"] == 1
        assert data["status"] == "confirmed"
        assert "id" in data
    
    def test_create_booking_invalid_time_range(self, mock_regular_user):
        start = get_future_datetime(2)
        end = get_future_datetime(1)  # End before start
        
        response = client.post(
            "/bookings/",
            json={
                "room_id": 1,
                "start_time": start.isoformat(),
                "end_time": end.isoformat()
            }
        )
        assert response.status_code == 400
        assert "Invalid time range" in response.json()["detail"]
    
    def test_create_overlapping_booking(self, mock_regular_user, mock_another_user):
        start = get_future_datetime(1)
        end = get_future_datetime(3)
        
        # Create first booking
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="regular", user_id=1)
        response1 = client.post(
            "/bookings/",
            json={
                "room_id": 1,
                "start_time": start.isoformat(),
                "end_time": end.isoformat()
            }
        )
        assert response1.status_code == 201
        
        # Try to create overlapping booking
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="regular", user_id=2)
        overlap_start = get_future_datetime(2)
        overlap_end = get_future_datetime(4)
        response2 = client.post(
            "/bookings/",
            json={
                "room_id": 1,
                "start_time": overlap_start.isoformat(),
                "end_time": overlap_end.isoformat()
            }
        )
        assert response2.status_code == 400
        assert "not available" in response2.json()["detail"].lower()
    
    def test_create_booking_different_rooms_same_time(self, mock_regular_user):
        start = get_future_datetime(1)
        end = get_future_datetime(2)
        
        # Create booking for room 1
        response1 = client.post(
            "/bookings/",
            json={
                "room_id": 1,
                "start_time": start.isoformat(),
                "end_time": end.isoformat()
            }
        )
        assert response1.status_code == 201
        
        # Create booking for room 2 at same time - should succeed
        response2 = client.post(
            "/bookings/",
            json={
                "room_id": 2,
                "start_time": start.isoformat(),
                "end_time": end.isoformat()
            }
        )
        assert response2.status_code == 201


class TestBookingRetrieval:
    """Test booking retrieval endpoints"""
    
    def test_list_my_bookings(self, mock_regular_user):
        # Create some bookings
        start1 = get_future_datetime(1)
        end1 = get_future_datetime(2)
        client.post("/bookings/", json={"room_id": 1, "start_time": start1.isoformat(), "end_time": end1.isoformat()})
        
        start2 = get_future_datetime(3)
        end2 = get_future_datetime(4)
        client.post("/bookings/", json={"room_id": 2, "start_time": start2.isoformat(), "end_time": end2.isoformat()})
        
        # List my bookings
        response = client.get("/bookings/me")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(booking["user_id"] == 1 for booking in data)
    
    def test_list_all_bookings_as_admin(self, mock_regular_user, mock_admin):
        # Create booking as regular user
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="regular", user_id=1)
        start = get_future_datetime(1)
        end = get_future_datetime(2)
        client.post("/bookings/", json={"room_id": 1, "start_time": start.isoformat(), "end_time": end.isoformat()})
        
        # List all bookings as admin
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="admin", user_id=100)
        response = client.get("/bookings/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
    
    def test_list_all_bookings_as_regular_user_forbidden(self, mock_regular_user):
        response = client.get("/bookings/")
        assert response.status_code == 403
    
    def test_list_all_bookings_as_auditor(self, mock_auditor):
        response = client.get("/bookings/")
        assert response.status_code == 200
    
    def test_user_booking_history(self, mock_regular_user, mock_admin):
        # Create booking as user 1
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="regular", user_id=1)
        start = get_future_datetime(1)
        end = get_future_datetime(2)
        client.post("/bookings/", json={"room_id": 1, "start_time": start.isoformat(), "end_time": end.isoformat()})
        
        # Get history as admin
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="admin", user_id=100)
        response = client.get("/bookings/user/1")
        assert response.status_code == 200
        data = response.json()
        assert all(booking["user_id"] == 1 for booking in data)
    
    def test_user_booking_history_as_regular_user_forbidden(self, mock_regular_user):
        response = client.get("/bookings/user/1")
        assert response.status_code == 403


class TestBookingUpdate:
    """Test booking update endpoints"""
    
    def test_update_own_booking(self, mock_regular_user):
        # Create booking
        start = get_future_datetime(1)
        end = get_future_datetime(2)
        create_response = client.post(
            "/bookings/",
            json={"room_id": 1, "start_time": start.isoformat(), "end_time": end.isoformat()}
        )
        booking_id = create_response.json()["id"]
        
        # Update booking
        new_start = get_future_datetime(3)
        new_end = get_future_datetime(4)
        response = client.put(
            f"/bookings/{booking_id}",
            json={"start_time": new_start.isoformat(), "end_time": new_end.isoformat()}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == booking_id
    
    def test_update_booking_to_different_room(self, mock_regular_user):
        # Create booking
        start = get_future_datetime(1)
        end = get_future_datetime(2)
        create_response = client.post(
            "/bookings/",
            json={"room_id": 1, "start_time": start.isoformat(), "end_time": end.isoformat()}
        )
        booking_id = create_response.json()["id"]
        
        # Update to different room
        response = client.put(
            f"/bookings/{booking_id}",
            json={"room_id": 2}
        )
        assert response.status_code == 200
        assert response.json()["room_id"] == 2
    
    def test_update_others_booking_forbidden(self, mock_regular_user, mock_another_user):
        # Create booking as user 1
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="regular", user_id=1)
        start = get_future_datetime(1)
        end = get_future_datetime(2)
        create_response = client.post(
            "/bookings/",
            json={"room_id": 1, "start_time": start.isoformat(), "end_time": end.isoformat()}
        )
        booking_id = create_response.json()["id"]
        
        # Try to update as user 2
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="regular", user_id=2)
        new_start = get_future_datetime(3)
        new_end = get_future_datetime(4)
        response = client.put(
            f"/bookings/{booking_id}",
            json={"start_time": new_start.isoformat(), "end_time": new_end.isoformat()}
        )
        assert response.status_code == 403
    
    def test_update_others_booking_as_admin(self, mock_regular_user, mock_admin):
        # Create booking as regular user
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="regular", user_id=1)
        start = get_future_datetime(1)
        end = get_future_datetime(2)
        create_response = client.post(
            "/bookings/",
            json={"room_id": 1, "start_time": start.isoformat(), "end_time": end.isoformat()}
        )
        booking_id = create_response.json()["id"]
        
        # Update as admin
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="admin", user_id=100)
        new_start = get_future_datetime(5)
        new_end = get_future_datetime(6)
        response = client.put(
            f"/bookings/{booking_id}",
            json={"start_time": new_start.isoformat(), "end_time": new_end.isoformat()}
        )
        assert response.status_code == 200
    
    def test_update_booking_with_conflict(self, mock_regular_user):
        # Create two bookings
        start1 = get_future_datetime(1)
        end1 = get_future_datetime(2)
        response1 = client.post(
            "/bookings/",
            json={"room_id": 1, "start_time": start1.isoformat(), "end_time": end1.isoformat()}
        )
        booking1_id = response1.json()["id"]
        
        start2 = get_future_datetime(3)
        end2 = get_future_datetime(4)
        client.post(
            "/bookings/",
            json={"room_id": 1, "start_time": start2.isoformat(), "end_time": end2.isoformat()}
        )
        
        # Try to update first booking to overlap with second
        response = client.put(
            f"/bookings/{booking1_id}",
            json={"start_time": start2.isoformat(), "end_time": end2.isoformat()}
        )
        assert response.status_code == 400
        assert "not available" in response.json()["detail"].lower()
    
    def test_update_nonexistent_booking(self, mock_regular_user):
        start = get_future_datetime(1)
        end = get_future_datetime(2)
        response = client.put(
            "/bookings/99999",
            json={"start_time": start.isoformat(), "end_time": end.isoformat()}
        )
        assert response.status_code == 404


class TestBookingCancellation:
    """Test booking cancellation endpoints"""
    
    def test_cancel_own_booking(self, mock_regular_user):
        # Create booking
        start = get_future_datetime(1)
        end = get_future_datetime(2)
        create_response = client.post(
            "/bookings/",
            json={"room_id": 1, "start_time": start.isoformat(), "end_time": end.isoformat()}
        )
        booking_id = create_response.json()["id"]
        
        # Cancel booking
        response = client.delete(f"/bookings/{booking_id}")
        assert response.status_code == 204
    
    def test_cancel_others_booking_forbidden(self, mock_regular_user, mock_another_user):
        # Create booking as user 1
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="regular", user_id=1)
        start = get_future_datetime(1)
        end = get_future_datetime(2)
        create_response = client.post(
            "/bookings/",
            json={"room_id": 1, "start_time": start.isoformat(), "end_time": end.isoformat()}
        )
        booking_id = create_response.json()["id"]
        
        # Try to cancel as user 2
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="regular", user_id=2)
        response = client.delete(f"/bookings/{booking_id}")
        assert response.status_code == 403
    
    def test_cancel_others_booking_as_admin(self, mock_regular_user, mock_admin):
        # Create booking as regular user
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="regular", user_id=1)
        start = get_future_datetime(1)
        end = get_future_datetime(2)
        create_response = client.post(
            "/bookings/",
            json={"room_id": 1, "start_time": start.isoformat(), "end_time": end.isoformat()}
        )
        booking_id = create_response.json()["id"]
        
        # Cancel as admin
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="admin", user_id=100)
        response = client.delete(f"/bookings/{booking_id}")
        assert response.status_code == 204
    
    def test_cancel_nonexistent_booking(self, mock_regular_user):
        response = client.delete("/bookings/99999")
        assert response.status_code == 404


class TestAvailabilityCheck:
    """Test availability checking endpoints"""
    
    def test_check_availability_free_slot(self, mock_regular_user):
        start = get_future_datetime(1)
        end = get_future_datetime(2)
        
        response = client.get(
            f"/bookings/availability?room_id=1&start_time={start.isoformat()}&end_time={end.isoformat()}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is True
        assert data["room_id"] == 1
    
    def test_check_availability_booked_slot(self, mock_regular_user):
        # Create booking
        start = get_future_datetime(1)
        end = get_future_datetime(2)
        client.post(
            "/bookings/",
            json={"room_id": 1, "start_time": start.isoformat(), "end_time": end.isoformat()}
        )
        
        # Check availability for overlapping time
        check_start = get_future_datetime(1.5)
        check_end = get_future_datetime(2.5)
        response = client.get(
            f"/bookings/availability?room_id=1&start_time={check_start.isoformat()}&end_time={check_end.isoformat()}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is False


# Import dependency to clean up
from app.deps import get_current_token_data
