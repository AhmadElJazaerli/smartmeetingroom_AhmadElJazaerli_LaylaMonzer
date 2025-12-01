from contextlib import asynccontextmanager
from datetime import datetime
from typing import List
import json
import pika

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from sqlalchemy.orm import Session

from common.config import get_settings
from common.database import Base, engine, get_db
from common.dependencies import get_current_active_user
from common.logging_middleware import add_audit_middleware
from common.models import Booking, RoleEnum, Room, User
from common.rate_limit import apply_rate_limiter, limiter
from common.schemas import BookingCreate, BookingRead, BookingUpdate

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.run_db_migrations:
        Base.metadata.create_all(bind=engine)
    yield


def create_app() -> FastAPI:
    fastapi_app = FastAPI(title="Bookings Service", version="0.2.0", lifespan=lifespan)
    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    apply_rate_limiter(fastapi_app)
    add_audit_middleware(fastapi_app, "bookings")
    return fastapi_app


app = create_app()


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "bookings"}


@app.get("/bookings", response_model=List[BookingRead])
@limiter.limit("30/minute")
def list_bookings(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> List[Booking]:
    if current_user.role not in {RoleEnum.ADMIN, RoleEnum.FACILITY_MANAGER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return db.query(Booking).order_by(Booking.start_time.desc()).all()


def _ensure_availability(db: Session, room_id: int, start: datetime, end: datetime, exclude_booking_id: int | None = None) -> None:
    overlap_query = db.query(Booking).filter(
        Booking.room_id == room_id,
        Booking.start_time < end,
        Booking.end_time > start,
    )
    if exclude_booking_id:
        overlap_query = overlap_query.filter(Booking.id != exclude_booking_id)
    if overlap_query.first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Room already booked for that slot")


@app.post("/bookings", response_model=BookingRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
def create_booking(
    request: Request,
    booking_in: BookingCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Booking:
    if booking_in.end_time <= booking_in.start_time:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="End time must be after start time")
    room = db.query(Room).filter(Room.id == booking_in.room_id, Room.is_active.is_(True)).first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found or inactive")

    _ensure_availability(db, booking_in.room_id, booking_in.start_time, booking_in.end_time)
    booking = Booking(
        user_id=current_user.id,
        **booking_in.model_dump(),
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)

    import logging
    logger = logging.getLogger("rabbitmq_debug")
    logger.setLevel(logging.INFO)

    # RabbitMQ debug logging
    logger.info("[RabbitMQ] Preparing to send booking_created message...")
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host="rabbitmq"))
        logger.info("[RabbitMQ] Connection established.")
        channel = connection.channel()
        channel.queue_declare(queue="bookings", durable=True)
        logger.info("[RabbitMQ] Durable queue declared.")
        message = {
            "event": "booking_created",
            "booking_id": booking.id,
            "user_id": booking.user_id,
            "room_id": booking.room_id,
            "start_time": str(booking.start_time),
            "end_time": str(booking.end_time)
        }
        logger.info(f"[RabbitMQ] Sending message: {message}")
        channel.basic_publish(
            exchange="",
            routing_key="bookings",
            body=json.dumps(message),
            properties=pika.BasicProperties(delivery_mode=2)  # make message persistent
        )
        logger.info("[RabbitMQ] Message sent.")
        connection.close()
        logger.info("[RabbitMQ] Connection closed.")
    except Exception as e:
        logger.error(f"[RabbitMQ] Error: {e}")

    return booking


@app.put("/bookings/{booking_id}", response_model=BookingRead)
@limiter.limit("20/minute")
def update_booking(
    request: Request,
    booking_id: int,
    booking_update: BookingUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Booking:
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    if current_user.role not in {RoleEnum.ADMIN, RoleEnum.FACILITY_MANAGER} and booking.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    data = booking_update.model_dump(exclude_unset=True)
    room_id = data.get("room_id", booking.room_id)
    start = data.get("start_time", booking.start_time)
    end = data.get("end_time", booking.end_time)
    if end <= start:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="End time must be after start time")

    _ensure_availability(db, room_id, start, end, exclude_booking_id=booking.id)

    for key, value in data.items():
        setattr(booking, key, value)
    db.commit()
    db.refresh(booking)
    return booking


@app.delete("/bookings/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("20/minute")
def delete_booking(
    request: Request,
    booking_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> None:
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    if current_user.role not in {RoleEnum.ADMIN, RoleEnum.FACILITY_MANAGER} and booking.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    db.delete(booking)
    db.commit()


@app.get("/bookings/availability")
@limiter.limit("40/minute")
def check_availability(
    request: Request,
    room_id: int,
    start_time: datetime = Query(...),
    end_time: datetime = Query(...),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    _ensure_availability(db, room_id, start_time, end_time)
    return {"available": True}


@app.get("/analytics/rooms/popularity")
@limiter.limit("30/minute")
def room_popularity(
    request: Request,
    limit: int = Query(5, ge=1, le=25),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> list[dict[str, int | str]]:
    if current_user.role not in {RoleEnum.ADMIN, RoleEnum.FACILITY_MANAGER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    rows = (
        db.query(Room.id, Room.name, func.count(Booking.id).label("booking_count"))
        .outerjoin(Booking, Booking.room_id == Room.id)
        .group_by(Room.id)
        .order_by(func.count(Booking.id).desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "room_id": room_id,
            "room_name": room_name,
            "booking_count": booking_count,
        }
        for room_id, room_name, booking_count in rows
    ]


@app.get("/analytics/users/activity")
@limiter.limit("30/minute")
def user_activity(
    request: Request,
    limit: int = Query(5, ge=1, le=50),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> list[dict[str, int | str]]:
    if current_user.role not in {RoleEnum.ADMIN, RoleEnum.FACILITY_MANAGER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    rows = (
        db.query(User.id, User.username, func.count(Booking.id).label("booking_count"))
        .outerjoin(Booking, Booking.user_id == User.id)
        .group_by(User.id)
        .order_by(func.count(Booking.id).desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "user_id": user_id,
            "username": username,
            "booking_count": booking_count,
        }
        for user_id, username, booking_count in rows
    ]
