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
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_reviews.db"
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
def mock_admin():
    """Mock admin authentication"""
    from app.deps import get_current_token_data
    app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="admin", user_id=100)
    yield
    app.dependency_overrides.pop(get_current_token_data, None)


@pytest.fixture
def mock_moderator():
    """Mock moderator authentication"""
    from app.deps import get_current_token_data
    app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="moderator", user_id=200)
    yield
    app.dependency_overrides.pop(get_current_token_data, None)


class TestReviewCreation:
    """Test review creation endpoints"""
    
    def test_create_review_success(self, mock_regular_user):
        response = client.post(
            "/reviews/",
            json={
                "room_id": 1,
                "rating": 5,
                "comment": "Excellent meeting room!"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["room_id"] == 1
        assert data["user_id"] == 1
        assert data["rating"] == 5
        assert data["comment"] == "Excellent meeting room!"
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
    
    def test_create_review_without_comment(self, mock_regular_user):
        response = client.post(
            "/reviews/",
            json={
                "room_id": 1,
                "rating": 4
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["rating"] == 4
        assert data["comment"] is None
    
    def test_create_review_invalid_rating_too_low(self, mock_regular_user):
        response = client.post(
            "/reviews/",
            json={
                "room_id": 1,
                "rating": 0,
                "comment": "Invalid rating"
            }
        )
        assert response.status_code == 422  # Validation error
    
    def test_create_review_invalid_rating_too_high(self, mock_regular_user):
        response = client.post(
            "/reviews/",
            json={
                "room_id": 1,
                "rating": 6,
                "comment": "Invalid rating"
            }
        )
        assert response.status_code == 422  # Validation error
    
    def test_create_duplicate_review(self, mock_regular_user):
        # Create first review
        client.post(
            "/reviews/",
            json={
                "room_id": 1,
                "rating": 5,
                "comment": "First review"
            }
        )
        
        # Try to create duplicate review for same room
        response = client.post(
            "/reviews/",
            json={
                "room_id": 1,
                "rating": 4,
                "comment": "Duplicate review"
            }
        )
        assert response.status_code == 400
        assert "already reviewed" in response.json()["detail"].lower()
    
    def test_create_review_different_rooms(self, mock_regular_user):
        # Create review for room 1
        response1 = client.post(
            "/reviews/",
            json={
                "room_id": 1,
                "rating": 5,
                "comment": "Room 1 review"
            }
        )
        assert response1.status_code == 201
        
        # Create review for room 2 - should succeed
        response2 = client.post(
            "/reviews/",
            json={
                "room_id": 2,
                "rating": 4,
                "comment": "Room 2 review"
            }
        )
        assert response2.status_code == 201


class TestReviewRetrieval:
    """Test review retrieval endpoints"""
    
    def test_list_all_reviews(self, mock_regular_user):
        # Create some reviews
        client.post("/reviews/", json={"room_id": 1, "rating": 5, "comment": "Great!"})
        client.post("/reviews/", json={"room_id": 2, "rating": 4, "comment": "Good"})
        
        # List all reviews
        response = client.get("/reviews/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
    
    def test_list_reviews_filtered_by_room(self, mock_regular_user, mock_another_user):
        # Create reviews for different rooms
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="regular", user_id=1)
        client.post("/reviews/", json={"room_id": 1, "rating": 5, "comment": "Room 1"})
        
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="regular", user_id=2)
        client.post("/reviews/", json={"room_id": 2, "rating": 4, "comment": "Room 2"})
        
        # Filter by room_id
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="regular", user_id=1)
        response = client.get("/reviews/?room_id=1")
        assert response.status_code == 200
        data = response.json()
        assert all(review["room_id"] == 1 for review in data)
    
    def test_list_my_reviews(self, mock_regular_user, mock_another_user):
        # Create reviews as user 1
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="regular", user_id=1)
        client.post("/reviews/", json={"room_id": 1, "rating": 5})
        client.post("/reviews/", json={"room_id": 2, "rating": 4})
        
        # Create review as user 2
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="regular", user_id=2)
        client.post("/reviews/", json={"room_id": 3, "rating": 3})
        
        # List user 1's reviews
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="regular", user_id=1)
        response = client.get("/reviews/me")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(review["user_id"] == 1 for review in data)
    
    def test_get_review_by_id(self, mock_regular_user):
        # Create review
        create_response = client.post(
            "/reviews/",
            json={"room_id": 1, "rating": 5, "comment": "Test review"}
        )
        review_id = create_response.json()["id"]
        
        # Get review by ID
        response = client.get(f"/reviews/{review_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == review_id
        assert data["rating"] == 5
        assert data["comment"] == "Test review"
    
    def test_get_nonexistent_review(self, mock_regular_user):
        response = client.get("/reviews/99999")
        assert response.status_code == 404
    
    def test_get_room_stats_no_reviews(self, mock_regular_user):
        response = client.get("/reviews/room/1/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["room_id"] == 1
        assert data["average_rating"] == 0.0
        assert data["total_reviews"] == 0
    
    def test_get_room_stats_with_reviews(self, mock_regular_user, mock_another_user):
        # Create reviews for room 1
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="regular", user_id=1)
        client.post("/reviews/", json={"room_id": 1, "rating": 5})
        
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="regular", user_id=2)
        client.post("/reviews/", json={"room_id": 1, "rating": 3})
        
        # Get stats
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="regular", user_id=1)
        response = client.get("/reviews/room/1/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["room_id"] == 1
        assert data["average_rating"] == 4.0  # (5 + 3) / 2
        assert data["total_reviews"] == 2


class TestReviewUpdate:
    """Test review update endpoints"""
    
    def test_update_own_review(self, mock_regular_user):
        # Create review
        create_response = client.post(
            "/reviews/",
            json={"room_id": 1, "rating": 3, "comment": "Initial comment"}
        )
        review_id = create_response.json()["id"]
        
        # Update review
        response = client.put(
            f"/reviews/{review_id}",
            json={"rating": 5, "comment": "Updated comment"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["rating"] == 5
        assert data["comment"] == "Updated comment"
    
    def test_update_review_rating_only(self, mock_regular_user):
        # Create review
        create_response = client.post(
            "/reviews/",
            json={"room_id": 1, "rating": 3, "comment": "Original"}
        )
        review_id = create_response.json()["id"]
        
        # Update only rating
        response = client.put(
            f"/reviews/{review_id}",
            json={"rating": 4}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["rating"] == 4
        assert data["comment"] == "Original"
    
    def test_update_review_comment_only(self, mock_regular_user):
        # Create review
        create_response = client.post(
            "/reviews/",
            json={"room_id": 1, "rating": 4, "comment": "Original"}
        )
        review_id = create_response.json()["id"]
        
        # Update only comment
        response = client.put(
            f"/reviews/{review_id}",
            json={"comment": "New comment"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["rating"] == 4
        assert data["comment"] == "New comment"
    
    def test_update_others_review_forbidden(self, mock_regular_user, mock_another_user):
        # Create review as user 1
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="regular", user_id=1)
        create_response = client.post(
            "/reviews/",
            json={"room_id": 1, "rating": 5, "comment": "User 1 review"}
        )
        review_id = create_response.json()["id"]
        
        # Try to update as user 2
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="regular", user_id=2)
        response = client.put(
            f"/reviews/{review_id}",
            json={"rating": 1, "comment": "Malicious update"}
        )
        assert response.status_code == 403
    
    def test_update_others_review_as_admin(self, mock_regular_user, mock_admin):
        # Create review as regular user
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="regular", user_id=1)
        create_response = client.post(
            "/reviews/",
            json={"room_id": 1, "rating": 5, "comment": "Original"}
        )
        review_id = create_response.json()["id"]
        
        # Update as admin
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="admin", user_id=100)
        response = client.put(
            f"/reviews/{review_id}",
            json={"comment": "Moderated by admin"}
        )
        assert response.status_code == 200
        assert response.json()["comment"] == "Moderated by admin"
    
    def test_update_others_review_as_moderator(self, mock_regular_user, mock_moderator):
        # Create review as regular user
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="regular", user_id=1)
        create_response = client.post(
            "/reviews/",
            json={"room_id": 1, "rating": 5, "comment": "Original"}
        )
        review_id = create_response.json()["id"]
        
        # Update as moderator
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="moderator", user_id=200)
        response = client.put(
            f"/reviews/{review_id}",
            json={"comment": "Moderated"}
        )
        assert response.status_code == 200
    
    def test_update_nonexistent_review(self, mock_regular_user):
        response = client.put(
            "/reviews/99999",
            json={"rating": 5}
        )
        assert response.status_code == 404
    
    def test_update_review_invalid_rating(self, mock_regular_user):
        # Create review
        create_response = client.post(
            "/reviews/",
            json={"room_id": 1, "rating": 3}
        )
        review_id = create_response.json()["id"]
        
        # Try to update with invalid rating
        response = client.put(
            f"/reviews/{review_id}",
            json={"rating": 10}
        )
        assert response.status_code == 422  # Validation error


class TestReviewDeletion:
    """Test review deletion endpoints"""
    
    def test_delete_own_review(self, mock_regular_user):
        # Create review
        create_response = client.post(
            "/reviews/",
            json={"room_id": 1, "rating": 5, "comment": "To delete"}
        )
        review_id = create_response.json()["id"]
        
        # Delete review
        response = client.delete(f"/reviews/{review_id}")
        assert response.status_code == 204
        
        # Verify deletion
        get_response = client.get(f"/reviews/{review_id}")
        assert get_response.status_code == 404
    
    def test_delete_others_review_forbidden(self, mock_regular_user, mock_another_user):
        # Create review as user 1
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="regular", user_id=1)
        create_response = client.post(
            "/reviews/",
            json={"room_id": 1, "rating": 5}
        )
        review_id = create_response.json()["id"]
        
        # Try to delete as user 2
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="regular", user_id=2)
        response = client.delete(f"/reviews/{review_id}")
        assert response.status_code == 403
    
    def test_delete_others_review_as_admin(self, mock_regular_user, mock_admin):
        # Create review as regular user
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="regular", user_id=1)
        create_response = client.post(
            "/reviews/",
            json={"room_id": 1, "rating": 5, "comment": "Inappropriate content"}
        )
        review_id = create_response.json()["id"]
        
        # Delete as admin
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="admin", user_id=100)
        response = client.delete(f"/reviews/{review_id}")
        assert response.status_code == 204
    
    def test_delete_others_review_as_moderator(self, mock_regular_user, mock_moderator):
        # Create review as regular user
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="regular", user_id=1)
        create_response = client.post(
            "/reviews/",
            json={"room_id": 1, "rating": 1, "comment": "Spam"}
        )
        review_id = create_response.json()["id"]
        
        # Delete as moderator
        app.dependency_overrides[get_current_token_data] = lambda: create_mock_token_data(role="moderator", user_id=200)
        response = client.delete(f"/reviews/{review_id}")
        assert response.status_code == 204
    
    def test_delete_nonexistent_review(self, mock_regular_user):
        response = client.delete("/reviews/99999")
        assert response.status_code == 404


# Import dependency to clean up
from app.deps import get_current_token_data
