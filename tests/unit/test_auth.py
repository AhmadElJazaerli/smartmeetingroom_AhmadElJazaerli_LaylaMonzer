"""Unit tests for authentication functions."""
import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from jose import jwt

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from common.auth import (
    authenticate_user,
    create_access_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from common.config import get_settings
from common.models import RoleEnum, User

settings = get_settings()


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_password_hash_and_verify(self):
        """Test that password can be hashed and verified."""
        password = "MySecurePassword123!"
        hashed = get_password_hash(password)
        
        assert hashed != password
        assert verify_password(password, hashed) is True
        assert verify_password("WrongPassword", hashed) is False

    def test_same_password_different_hashes(self):
        """Test that the same password generates different hashes (salt)."""
        password = "TestPassword123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        assert hash1 != hash2
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestJWTTokens:
    """Test JWT token creation and decoding."""

    def test_create_access_token(self):
        """Test JWT token creation with valid data."""
        data = {"sub": "testuser", "role": "admin"}
        token = create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Decode and verify
        decoded = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        assert decoded["sub"] == "testuser"
        assert decoded["role"] == "admin"
        assert "exp" in decoded

    def test_create_token_with_custom_expiry(self):
        """Test token creation with custom expiration."""
        data = {"sub": "user123"}
        expires_delta = timedelta(minutes=30)
        token = create_access_token(data, expires_delta)
        
        decoded = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        
        # Just verify the token has an expiration field
        assert "exp" in decoded
        assert decoded["exp"] > datetime.utcnow().timestamp()

    def test_decode_token_valid(self):
        """Test decoding a valid token."""
        data = {"sub": "testuser", "role": "regular"}
        token = create_access_token(data)
        
        decoded = decode_token(token)
        assert decoded["sub"] == "testuser"
        assert decoded["role"] == "regular"

    def test_decode_token_invalid(self):
        """Test decoding an invalid token raises exception."""
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            decode_token("invalid.token.here")
        
        assert exc_info.value.status_code == 401
        assert "Invalid token" in str(exc_info.value.detail)

    def test_decode_token_expired(self):
        """Test decoding an expired token raises exception."""
        from fastapi import HTTPException
        
        data = {"sub": "testuser"}
        # Create token that expired 1 hour ago
        expires_delta = timedelta(hours=-1)
        token = create_access_token(data, expires_delta)
        
        with pytest.raises(HTTPException) as exc_info:
            decode_token(token)
        
        assert exc_info.value.status_code == 401


class TestUserAuthentication:
    """Test user authentication logic."""

    def test_authenticate_user_success(self):
        """Test successful user authentication."""
        mock_db = MagicMock()
        password = "TestPass123"
        hashed_password = get_password_hash(password)
        
        mock_user = User(
            id=1,
            username="testuser",
            email="test@example.com",
            name="Test User",
            role=RoleEnum.REGULAR,
            hashed_password=hashed_password,
        )
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        result = authenticate_user(mock_db, "testuser", password)
        
        assert result is not None
        assert result.username == "testuser"
        assert result.id == 1

    def test_authenticate_user_wrong_password(self):
        """Test authentication fails with wrong password."""
        mock_db = MagicMock()
        hashed_password = get_password_hash("CorrectPassword")
        
        mock_user = User(
            id=1,
            username="testuser",
            email="test@example.com",
            name="Test User",
            role=RoleEnum.REGULAR,
            hashed_password=hashed_password,
        )
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        result = authenticate_user(mock_db, "testuser", "WrongPassword")
        
        assert result is None

    def test_authenticate_user_not_found(self):
        """Test authentication fails when user doesn't exist."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = authenticate_user(mock_db, "nonexistent", "anypassword")
        
        assert result is None
