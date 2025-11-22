import os
os.environ["TESTING"] = "1"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db
from app.auth import TokenData

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_rooms.db"
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


def create_mock_token_data(role="admin", user_id=1, username="testuser"):
    """Helper to create mock token data for auth bypass"""
    return TokenData(username=username, user_id=user_id, role=role)


@pytest.fixture
def mock_admin():
    """Mock admin authentication"""
    from app.deps import get_current_token_data
    app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="admin")
    yield
    app.dependency_overrides.pop(get_current_token_data, None)


@pytest.fixture
def mock_facility_manager():
    """Mock facility manager authentication"""
    from app.deps import get_current_token_data
    app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="facility_manager")
    yield
    app.dependency_overrides.pop(get_current_token_data, None)


@pytest.fixture
def mock_regular_user():
    """Mock regular user authentication"""
    from app.deps import get_current_token_data
    app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="regular", user_id=2)
    yield
    app.dependency_overrides.pop(get_current_token_data, None)


class TestRoomCreation:
    """Test room creation endpoints"""
    
    def test_create_room_as_admin(self, mock_admin):
        response = client.post(
            "/rooms/",
            json={
                "name": "Conference Room A",
                "capacity": 10,
                "equipment": "projector, whiteboard",
                "location": "Building 1, Floor 2"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Conference Room A"
        assert data["capacity"] == 10
        assert data["is_available"] is True
        assert data["is_out_of_service"] is False
        assert "id" in data
    
    def test_create_room_as_facility_manager(self, mock_facility_manager):
        response = client.post(
            "/rooms/",
            json={
                "name": "Meeting Room B",
                "capacity": 5,
                "equipment": "TV",
                "location": "Building 2"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Meeting Room B"
    
    def test_create_room_as_regular_user_forbidden(self, mock_regular_user):
        response = client.post(
            "/rooms/",
            json={
                "name": "Room C",
                "capacity": 8,
                "location": "Building 3"
            }
        )
        assert response.status_code == 403
    
    def test_create_duplicate_room(self, mock_admin):
        client.post(
            "/rooms/",
            json={
                "name": "Duplicate Room",
                "capacity": 6,
                "location": "Building 1"
            }
        )
        response = client.post(
            "/rooms/",
            json={
                "name": "Duplicate Room",
                "capacity": 8,
                "location": "Building 2"
            }
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]


class TestRoomRetrieval:
    """Test room retrieval endpoints"""
    
    def test_list_all_rooms(self, mock_regular_user, mock_admin):
        # Create some rooms as admin
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="admin")
        client.post("/rooms/", json={"name": "Room 1", "capacity": 5, "location": "Floor 1"})
        client.post("/rooms/", json={"name": "Room 2", "capacity": 10, "location": "Floor 2"})
        
        # List as regular user
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="regular")
        response = client.get("/rooms/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
    
    def test_get_room_by_id(self, mock_admin, mock_regular_user):
        # Create room as admin
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="admin")
        create_response = client.post(
            "/rooms/",
            json={"name": "Test Room", "capacity": 7, "location": "Building A"}
        )
        room_id = create_response.json()["id"]
        
        # Get as regular user
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="regular")
        response = client.get(f"/rooms/{room_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Room"
        assert data["capacity"] == 7
    
    def test_get_nonexistent_room(self, mock_regular_user):
        response = client.get("/rooms/99999")
        assert response.status_code == 404
    
    def test_get_available_rooms(self, mock_admin, mock_regular_user):
        # Create rooms
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="admin")
        client.post("/rooms/", json={"name": "Available Room", "capacity": 10, "location": "Floor 1", "equipment": "projector"})
        client.post("/rooms/", json={"name": "Small Room", "capacity": 4, "location": "Floor 1"})
        
        # Get available rooms
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="regular")
        response = client.get("/rooms/available")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
    
    def test_filter_by_capacity(self, mock_admin, mock_regular_user):
        # Create rooms with different capacities
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="admin")
        client.post("/rooms/", json={"name": "Small", "capacity": 4, "location": "Floor 1"})
        client.post("/rooms/", json={"name": "Large", "capacity": 20, "location": "Floor 2"})
        
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="regular")
        response = client.get("/rooms/available?capacity=10")
        assert response.status_code == 200
        data = response.json()
        assert all(room["capacity"] >= 10 for room in data)
    
    def test_filter_by_location(self, mock_admin, mock_regular_user):
        # Create rooms in different locations
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="admin")
        client.post("/rooms/", json={"name": "Room A", "capacity": 5, "location": "Building A"})
        client.post("/rooms/", json={"name": "Room B", "capacity": 5, "location": "Building B"})
        
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="regular")
        response = client.get("/rooms/available?location=Building A")
        assert response.status_code == 200
        data = response.json()
        assert all(room["location"] == "Building A" for room in data)
    
    def test_filter_by_equipment(self, mock_admin, mock_regular_user):
        # Create rooms with equipment
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="admin")
        client.post("/rooms/", json={"name": "Tech Room", "capacity": 8, "location": "Floor 1", "equipment": "projector, microphone"})
        client.post("/rooms/", json={"name": "Basic Room", "capacity": 6, "location": "Floor 1", "equipment": "whiteboard"})
        
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="regular")
        response = client.get("/rooms/available?equipment=projector")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any("projector" in room.get("equipment", "").lower() for room in data)


class TestRoomUpdate:
    """Test room update endpoints"""
    
    def test_update_room_as_admin(self, mock_admin):
        # Create room
        create_response = client.post(
            "/rooms/",
            json={"name": "Update Test", "capacity": 5, "location": "Floor 1"}
        )
        room_id = create_response.json()["id"]
        
        # Update room
        response = client.put(
            f"/rooms/{room_id}",
            json={"capacity": 12, "equipment": "new projector"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["capacity"] == 12
        assert data["equipment"] == "new projector"
    
    def test_update_room_availability(self, mock_admin):
        # Create room
        create_response = client.post(
            "/rooms/",
            json={"name": "Availability Test", "capacity": 8, "location": "Floor 2"}
        )
        room_id = create_response.json()["id"]
        
        # Mark as unavailable
        response = client.put(
            f"/rooms/{room_id}",
            json={"is_available": False}
        )
        assert response.status_code == 200
        assert response.json()["is_available"] is False
    
    def test_update_room_out_of_service(self, mock_facility_manager):
        # Create room
        create_response = client.post(
            "/rooms/",
            json={"name": "Service Test", "capacity": 6, "location": "Floor 1"}
        )
        room_id = create_response.json()["id"]
        
        # Mark as out of service
        response = client.put(
            f"/rooms/{room_id}",
            json={"is_out_of_service": True}
        )
        assert response.status_code == 200
        assert response.json()["is_out_of_service"] is True
    
    def test_update_room_as_regular_user_forbidden(self, mock_admin, mock_regular_user):
        # Create room as admin
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="admin")
        create_response = client.post(
            "/rooms/",
            json={"name": "Forbidden Update", "capacity": 5, "location": "Floor 1"}
        )
        room_id = create_response.json()["id"]
        
        # Try to update as regular user
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="regular")
        response = client.put(
            f"/rooms/{room_id}",
            json={"capacity": 10}
        )
        assert response.status_code == 403
    
    def test_update_nonexistent_room(self, mock_admin):
        response = client.put(
            "/rooms/99999",
            json={"capacity": 10}
        )
        assert response.status_code == 404


class TestRoomDeletion:
    """Test room deletion endpoints"""
    
    def test_delete_room_as_admin(self, mock_admin):
        # Create room
        create_response = client.post(
            "/rooms/",
            json={"name": "To Delete", "capacity": 5, "location": "Floor 1"}
        )
        room_id = create_response.json()["id"]
        
        # Delete room
        response = client.delete(f"/rooms/{room_id}")
        assert response.status_code == 204
        
        # Verify deletion
        get_response = client.get(f"/rooms/{room_id}")
        assert get_response.status_code == 404
    
    def test_delete_room_as_regular_user_forbidden(self, mock_admin, mock_regular_user):
        # Create room as admin
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="admin")
        create_response = client.post(
            "/rooms/",
            json={"name": "Protected Room", "capacity": 5, "location": "Floor 1"}
        )
        room_id = create_response.json()["id"]
        
        # Try to delete as regular user
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="regular")
        response = client.delete(f"/rooms/{room_id}")
        assert response.status_code == 403
    
    def test_delete_nonexistent_room(self, mock_admin):
        response = client.delete("/rooms/99999")
        assert response.status_code == 404


class TestRoomStatus:
    """Test room status endpoint"""
    
    def test_get_room_status_available(self, mock_admin, mock_regular_user):
        # Create available room
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="admin")
        create_response = client.post(
            "/rooms/",
            json={"name": "Available Room", "capacity": 5, "location": "Floor 1"}
        )
        room_id = create_response.json()["id"]
        
        # Check status
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="regular")
        response = client.get(f"/rooms/{room_id}/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "available"
        assert data["room_id"] == room_id
    
    def test_get_room_status_out_of_service(self, mock_admin, mock_regular_user):
        # Create room and mark as out of service
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="admin")
        create_response = client.post(
            "/rooms/",
            json={"name": "Broken Room", "capacity": 5, "location": "Floor 1"}
        )
        room_id = create_response.json()["id"]
        client.put(f"/rooms/{room_id}", json={"is_out_of_service": True})
        
        # Check status
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="regular")
        response = client.get(f"/rooms/{room_id}/status")
        assert response.status_code == 200
        assert response.json()["status"] == "out_of_service"


# Import dependency to clean up
from app.deps import get_current_token_data
