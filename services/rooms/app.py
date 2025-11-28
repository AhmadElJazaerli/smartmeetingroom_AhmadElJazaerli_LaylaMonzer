from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional

from circuitbreaker import circuit
from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from common.cache import SimpleTTLCache
from common.config import get_settings
from common.database import Base, engine, get_db
from common.dependencies import get_current_active_user
from common.logging_middleware import add_audit_middleware
from common.models import Booking, RoleEnum, Room, User
from common.rate_limit import apply_rate_limiter, limiter
from common.schemas import RoomCreate, RoomRead, RoomUpdate

settings = get_settings()
room_status_cache: SimpleTTLCache[dict[str, str]] = SimpleTTLCache(ttl=settings.room_cache_ttl)
def _room_status_key(room_id: int) -> str:
    return f"room-status:{room_id}"


def _invalidate_room_cache(room_id: int) -> None:
    room_status_cache.pop(_room_status_key(room_id))


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.run_db_migrations:
        Base.metadata.create_all(bind=engine)
    yield


def create_app() -> FastAPI:
    fastapi_app = FastAPI(title="Rooms Service", version="0.2.0", lifespan=lifespan)
    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    apply_rate_limiter(fastapi_app)
    add_audit_middleware(fastapi_app, "rooms")
    return fastapi_app


app = create_app()


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "rooms"}


@app.post("/rooms", response_model=RoomRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
def add_room(
    request: Request,
    room_in: RoomCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Room:
    if current_user.role not in {RoleEnum.ADMIN, RoleEnum.FACILITY_MANAGER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    room = Room(**room_in.model_dump())
    db.add(room)
    db.commit()
    db.refresh(room)
    _invalidate_room_cache(room.id)
    return room


@app.get("/rooms", response_model=List[RoomRead])
@circuit(failure_threshold=5, recovery_timeout=60)
def list_rooms(
    request: Request,
    capacity: Optional[int] = None,
    location: Optional[str] = None,
    equipment: Optional[List[str]] = Query(default=None),
    db: Session = Depends(get_db),
) -> List[Room]:
    cache_key = f"room-list:{capacity}:{location}:{','.join(equipment or []) if equipment else ''}"
    from common.cache import SimpleTTLCache
    room_list_cache = getattr(list_rooms, "_cache", None)
    if room_list_cache is None:
        room_list_cache = SimpleTTLCache(ttl=60)  # 60 seconds TTL
        setattr(list_rooms, "_cache", room_list_cache)
    cached = room_list_cache.get(cache_key)
    if cached is not None:
        return cached

    query = db.query(Room).filter(Room.is_active.is_(True))
    if capacity:
        query = query.filter(Room.capacity >= capacity)
    if location:
        query = query.filter(Room.location.ilike(f"%{location}%"))
    rooms = query.all()
    if equipment:
        filtered = []
        for room in rooms:
            if set(equipment).issubset(set(room.equipment or [])):
                filtered.append(room)
        room_list_cache.set(cache_key, filtered)
        return filtered
    room_list_cache.set(cache_key, rooms)
    return rooms


@app.get("/rooms/{room_id}", response_model=RoomRead)
@limiter.limit("60/minute")
def get_room(request: Request, room_id: int, db: Session = Depends(get_db)) -> Room:
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    return room


@app.put("/rooms/{room_id}", response_model=RoomRead)
@limiter.limit("15/minute")
def update_room(
    request: Request,
    room_id: int,
    room_update: RoomUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Room:
    if current_user.role not in {RoleEnum.ADMIN, RoleEnum.FACILITY_MANAGER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    update_data = room_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(room, key, value)
    db.commit()
    db.refresh(room)
    _invalidate_room_cache(room.id)
    return room


@app.delete("/rooms/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("15/minute")
def delete_room(
    request: Request,
    room_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> None:
    if current_user.role not in {RoleEnum.ADMIN, RoleEnum.FACILITY_MANAGER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    db.delete(room)
    db.commit()
    _invalidate_room_cache(room_id)


@app.get("/rooms/{room_id}/status")
@limiter.limit("30/minute")
def room_status(
    request: Request,
    room_id: int,
    db: Session = Depends(get_db),
    force_refresh: bool = False,
) -> dict[str, str]:
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    cache_key = _room_status_key(room_id)
    if not force_refresh:
        cached = room_status_cache.get(cache_key)
        if cached:
            return cached
    now = datetime.utcnow()
    active_booking = (
        db.query(Booking)
        .filter(Booking.room_id == room_id, Booking.start_time <= now, Booking.end_time >= now)
        .first()
    )
    status_label = "booked" if active_booking else "available"
    payload = {
        "room_id": str(room_id),
        "status": status_label,
        "checked_at": now.isoformat(),
    }
    room_status_cache.set(cache_key, payload)
    return payload
