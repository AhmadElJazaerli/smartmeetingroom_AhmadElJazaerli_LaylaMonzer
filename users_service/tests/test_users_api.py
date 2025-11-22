import os
os.environ["TESTING"] = "1"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db
from app.auth import get_password_hash

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
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


@pytest.fixture
def admin_token():
    """Create an admin user and return authentication token"""
    response = client.post(
        "/auth/register",
        json={
            "name": "Admin User",
            "username": "admin",
            "email": "admin@test.com",
            "password": "admin123",
            "role": "admin"
        }
    )
    assert response.status_code == 201
    
    login_response = client.post(
        "/auth/login",
        data={"username": "admin", "password": "admin123"}
    )
    assert login_response.status_code == 200
    return login_response.json()["access_token"]


@pytest.fixture
def regular_user_token():
    """Create a regular user and return authentication token"""
    response = client.post(
        "/auth/register",
        json={
            "name": "Regular User",
            "username": "regular",
            "email": "regular@test.com",
            "password": "regular123",
            "role": "regular"
        }
    )
    assert response.status_code == 201
    
    login_response = client.post(
        "/auth/login",
        data={"username": "regular", "password": "regular123"}
    )
    assert login_response.status_code == 200
    return login_response.json()["access_token"]


class TestAuthentication:
    """Test authentication endpoints"""
    
    def test_register_user(self):
        response = client.post(
            "/auth/register",
            json={
                "name": "Test User",
                "username": "testuser",
                "email": "test@example.com",
                "password": "password123",
                "role": "regular"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
        assert data["role"] == "regular"
        assert "id" in data
        assert "hashed_password" not in data
    
    def test_register_duplicate_username(self):
        client.post(
            "/auth/register",
            json={
                "name": "User One",
                "username": "duplicate",
                "email": "user1@example.com",
                "password": "password123",
                "role": "regular"
            }
        )
        response = client.post(
            "/auth/register",
            json={
                "name": "User Two",
                "username": "duplicate",
                "email": "user2@example.com",
                "password": "password123",
                "role": "regular"
            }
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]
    
    def test_login_success(self):
        client.post(
            "/auth/register",
            json={
                "name": "Login Test",
                "username": "logintest",
                "email": "login@example.com",
                "password": "password123",
                "role": "regular"
            }
        )
        response = client.post(
            "/auth/login",
            data={"username": "logintest", "password": "password123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_wrong_password(self):
        client.post(
            "/auth/register",
            json={
                "name": "Login Test",
                "username": "logintest2",
                "email": "login2@example.com",
                "password": "password123",
                "role": "regular"
            }
        )
        response = client.post(
            "/auth/login",
            data={"username": "logintest2", "password": "wrongpassword"}
        )
        assert response.status_code == 401
    
    def test_login_nonexistent_user(self):
        response = client.post(
            "/auth/login",
            data={"username": "nonexistent", "password": "password123"}
        )
        assert response.status_code == 401


class TestUserEndpoints:
    """Test user management endpoints"""
    
    def test_get_profile(self, regular_user_token):
        response = client.get(
            "/users/me/profile",
            headers={"Authorization": f"Bearer {regular_user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "regular"
        assert data["email"] == "regular@test.com"
    
    def test_update_profile(self, regular_user_token):
        response = client.put(
            "/users/me/profile",
            headers={"Authorization": f"Bearer {regular_user_token}"},
            json={"name": "Updated Name", "email": "newemail@test.com"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["email"] == "newemail@test.com"
    
    def test_list_users_as_admin(self, admin_token):
        response = client.get(
            "/users/",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
    
    def test_list_users_as_regular_forbidden(self, regular_user_token):
        response = client.get(
            "/users/",
            headers={"Authorization": f"Bearer {regular_user_token}"}
        )
        assert response.status_code == 403
    
    def test_get_user_by_username(self, admin_token, regular_user_token):
        response = client.get(
            "/users/regular",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "regular"
    
    def test_get_nonexistent_user(self, admin_token):
        response = client.get(
            "/users/nonexistent",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404
    
    def test_delete_user_as_admin(self, admin_token):
        # Create a user to delete
        client.post(
            "/auth/register",
            json={
                "name": "To Delete",
                "username": "todelete",
                "email": "delete@test.com",
                "password": "password123",
                "role": "regular"
            }
        )
        response = client.delete(
            "/users/todelete",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 204
    
    def test_delete_user_as_regular_forbidden(self, regular_user_token, admin_token):
        response = client.delete(
            "/users/admin",
            headers={"Authorization": f"Bearer {regular_user_token}"}
        )
        assert response.status_code == 403
    
    def test_unauthorized_access(self):
        response = client.get("/users/me/profile")
        assert response.status_code == 401
