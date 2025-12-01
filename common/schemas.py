"""Pydantic schemas shared across the microservices."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field

from .models import RoleEnum


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: str
    role: RoleEnum


class UserBase(BaseModel):
    name: str = Field(..., max_length=100)
    username: str = Field(..., max_length=50)
    email: EmailStr
    role: RoleEnum = RoleEnum.REGULAR


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    role: Optional[RoleEnum] = None
    password: Optional[str] = Field(None, min_length=8)


class UserRead(UserBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class RoomBase(BaseModel):
    name: str
    capacity: int
    equipment: List[str]
    location: str
    is_active: bool = True


class RoomCreate(RoomBase):
    pass


class RoomUpdate(BaseModel):
    capacity: Optional[int] = None
    equipment: Optional[List[str]] = None
    location: Optional[str] = None
    is_active: Optional[bool] = None


class RoomRead(RoomBase):
    id: int

    model_config = {"from_attributes": True}


class BookingBase(BaseModel):
    room_id: int
    start_time: datetime
    end_time: datetime
    status: str = "confirmed"


class BookingCreate(BookingBase):
    pass


class BookingUpdate(BaseModel):
    room_id: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: Optional[str] = None


class BookingRead(BookingBase):
    id: int
    user_id: int

    model_config = {"from_attributes": True}


class ReviewBase(BaseModel):
    room_id: int
    rating: int = Field(..., ge=1, le=5)
    comment: str = Field(..., min_length=3, max_length=1000)


class ReviewCreate(ReviewBase):
    pass


class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = Field(None, min_length=3, max_length=1000)
    is_flagged: Optional[bool] = None


class ReviewRead(ReviewBase):
    id: int
    user_id: int
    is_flagged: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    username: str
    password: str


class ServicePing(BaseModel):
    status: str
    detail: str
