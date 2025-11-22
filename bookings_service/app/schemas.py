from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import List


class BookingBase(BaseModel):
    room_id: int
    start_time: datetime
    end_time: datetime


class BookingCreate(BookingBase):
    pass  # user_id from token


class BookingUpdate(BaseModel):
    room_id: int | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None


class BookingOut(BookingBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    status: str


class BookingList(BaseModel):
    bookings: List[BookingOut]
