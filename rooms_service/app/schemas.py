from pydantic import BaseModel, ConfigDict
from typing import Optional


class RoomBase(BaseModel):
    name: str
    capacity: int
    equipment: Optional[str] = None
    location: str


class RoomCreate(RoomBase):
    pass


class RoomUpdate(BaseModel):
    capacity: Optional[int] = None
    equipment: Optional[str] = None
    location: Optional[str] = None
    is_available: Optional[bool] = None
    is_out_of_service: Optional[bool] = None


class RoomOut(RoomBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    is_available: bool
    is_out_of_service: bool
