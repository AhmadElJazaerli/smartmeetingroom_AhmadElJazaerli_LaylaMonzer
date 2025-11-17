from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, List


class ReviewBase(BaseModel):
    room_id: int
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5")
    comment: Optional[str] = None


class ReviewCreate(ReviewBase):
    pass  # user_id from token


class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5, description="Rating from 1 to 5")
    comment: Optional[str] = None


class ReviewOut(ReviewBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class ReviewList(BaseModel):
    reviews: List[ReviewOut]
