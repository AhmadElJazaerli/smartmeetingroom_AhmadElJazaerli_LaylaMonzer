"""Unit tests for schema validation."""
import os
from datetime import datetime

import pytest
from pydantic import ValidationError

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from common.models import RoleEnum
from common.schemas import (
    BookingCreate,
    ReviewCreate,
    RoomCreate,
    UserCreate,
)


class TestUserSchemas:
    """Test user-related schemas."""

    def test_user_create_valid(self):
        """Test valid user creation schema."""
        user = UserCreate(
            name="John Doe",
            username="johndoe",
            email="john@example.com",
            password="SecurePass123!",
            role=RoleEnum.REGULAR,
        )
        
        assert user.name == "John Doe"
        assert user.username == "johndoe"
        assert user.email == "john@example.com"
        assert user.role == RoleEnum.REGULAR

    def test_user_create_default_role(self):
        """Test user creation with default role."""
        user = UserCreate(
            name="Jane Doe",
            username="janedoe",
            email="jane@example.com",
            password="SecurePass123!",
        )
        
        assert user.role == RoleEnum.REGULAR

    def test_user_create_invalid_email(self):
        """Test user creation with invalid email."""
        with pytest.raises(ValidationError):
            UserCreate(
                name="Test User",
                username="testuser",
                email="invalid-email",
                password="Password123",
            )


class TestRoomSchemas:
    """Test room-related schemas."""

    def test_room_create_valid(self):
        """Test valid room creation schema."""
        room = RoomCreate(
            name="Conference Room A",
            location="Building 1, Floor 2",
            capacity=10,
            equipment=["projector", "whiteboard"],
            is_active=True,
        )
        
        assert room.name == "Conference Room A"
        assert room.capacity == 10
        assert len(room.equipment) == 2
        assert room.is_active is True

    def test_room_create_default_values(self):
        """Test room creation with default values."""
        room = RoomCreate(
            name="Small Room",
            location="Building 2",
            capacity=4,
            equipment=[],
        )
        
        assert room.equipment == []
        assert room.is_active is True


class TestBookingSchemas:
    """Test booking-related schemas."""

    def test_booking_create_valid(self):
        """Test valid booking creation schema."""
        start = datetime(2025, 12, 1, 10, 0)
        end = datetime(2025, 12, 1, 11, 0)
        
        booking = BookingCreate(
            room_id=1,
            start_time=start,
            end_time=end,
        )
        
        assert booking.room_id == 1
        assert booking.start_time == start
        assert booking.end_time == end

    def test_booking_create_with_status(self):
        """Test booking creation with explicit status."""
        start = datetime(2025, 12, 1, 14, 0)
        end = datetime(2025, 12, 1, 15, 0)
        
        booking = BookingCreate(
            room_id=2,
            start_time=start,
            end_time=end,
            status="confirmed",
        )
        
        assert booking.status == "confirmed"


class TestReviewSchemas:
    """Test review-related schemas."""

    def test_review_create_valid(self):
        """Test valid review creation schema."""
        review = ReviewCreate(
            room_id=1,
            rating=5,
            comment="Excellent room with great equipment!",
        )
        
        assert review.room_id == 1
        assert review.rating == 5
        assert review.comment == "Excellent room with great equipment!"

    def test_review_create_minimal(self):
        """Test review creation with minimal required data."""
        review = ReviewCreate(
            room_id=2,
            rating=4,
            comment="Good",
        )
        
        assert review.room_id == 2
        assert review.rating == 4
        assert review.comment == "Good"

    def test_review_rating_validation(self):
        """Test review rating must be between 1 and 5."""
        # Valid ratings
        review_low = ReviewCreate(room_id=1, rating=1, comment="Bad")
        review_high = ReviewCreate(room_id=1, rating=5, comment="Excellent")
        
        assert review_low.rating == 1
        assert review_high.rating == 5
        
        # Invalid ratings should raise validation error
        with pytest.raises(ValidationError):
            ReviewCreate(room_id=1, rating=0, comment="Too low")
        
        with pytest.raises(ValidationError):
            ReviewCreate(room_id=1, rating=6, comment="Too high")
