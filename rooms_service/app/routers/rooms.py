from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas
from ..deps import require_role, get_current_token_data
from ..auth import TokenData

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.post("/", response_model=schemas.RoomOut, status_code=201)
def create_room(
    room_in: schemas.RoomCreate,
    db: Session = Depends(get_db),
    _: TokenData = Depends(require_role("admin", "facility_manager")),
):
    existing = db.query(models.Room).filter(models.Room.name == room_in.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Room already exists")
    room = models.Room(**room_in.dict())
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


@router.get("/", response_model=List[schemas.RoomOut])
def list_rooms(
    db: Session = Depends(get_db),
    _: TokenData = Depends(get_current_token_data),
):
    return db.query(models.Room).all()


@router.get("/available", response_model=List[schemas.RoomOut])
def get_available_rooms(
    capacity: Optional[int] = None,
    location: Optional[str] = None,
    equipment: Optional[str] = Query(default=None, description="comma-separated"),
    db: Session = Depends(get_db),
    _: TokenData = Depends(get_current_token_data),
):
    q = db.query(models.Room).filter(
        models.Room.is_available.is_(True), models.Room.is_out_of_service.is_(False)
    )
    if capacity is not None:
        q = q.filter(models.Room.capacity >= capacity)
    if location is not None:
        q = q.filter(models.Room.location == location)
    if equipment:
        for item in equipment.split(","):
            q = q.filter(models.Room.equipment.ilike(f"%{item.strip()}%"))
    return q.all()


@router.get("/{room_id}", response_model=schemas.RoomOut)
def get_room(
    room_id: int,
    db: Session = Depends(get_db),
    _: TokenData = Depends(get_current_token_data),
):
    room = db.query(models.Room).filter(models.Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room


@router.put("/{room_id}", response_model=schemas.RoomOut)
def update_room(
    room_id: int,
    room_update: schemas.RoomUpdate,
    db: Session = Depends(get_db),
    _: TokenData = Depends(require_role("admin", "facility_manager")),
):
    room = db.query(models.Room).filter(models.Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    for field, value in room_update.dict(exclude_unset=True).items():
        setattr(room, field, value)

    db.commit()
    db.refresh(room)
    return room


@router.delete("/{room_id}", status_code=204)
def delete_room(
    room_id: int,
    db: Session = Depends(get_db),
    _: TokenData = Depends(require_role("admin", "facility_manager")),
):
    room = db.query(models.Room).filter(models.Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    db.delete(room)
    db.commit()
    return None


@router.get("/{room_id}/status")
def room_status(
    room_id: int,
    db: Session = Depends(get_db),
    _: TokenData = Depends(get_current_token_data),
):
    room = db.query(models.Room).filter(models.Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    status = "out_of_service" if room.is_out_of_service else (
        "available" if room.is_available else "booked"
    )
    return {"room_id": room.id, "status": status}
