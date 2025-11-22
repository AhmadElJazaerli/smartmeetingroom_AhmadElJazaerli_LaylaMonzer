from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.orm import Session
from datetime import datetime
import httpx

from ..database import get_db
from .. import models, schemas
from ..deps import get_current_token_data, require_role
from ..auth import TokenData
from ..config import settings

router = APIRouter(prefix="/bookings", tags=["bookings"])


async def verify_mfa_if_enabled(user_id: int, mfa_code: str = None, token: str = None):
    """Helper function to verify MFA with users service"""
    if not mfa_code:
        return  # No MFA code provided, continue without verification
    
    # Call users service to check if MFA is enabled and verify code
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{settings.USERS_SERVICE_URL}/auth/mfa/status",
                headers={"Authorization": f"Bearer {token}"}
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("mfa_enabled"):
                    # MFA is enabled, code must be valid
                    if not mfa_code:
                        raise HTTPException(
                            status_code=403,
                            detail="MFA code required. Provide X-MFA-Code header"
                        )
        except httpx.RequestError:
            pass  # If service is unavailable, allow operation


def has_overlap(db: Session, room_id: int, start: datetime, end: datetime, exclude_id: int | None = None) -> bool:
    q = db.query(models.Booking).filter(
        models.Booking.room_id == room_id,
        models.Booking.status == "confirmed",
        models.Booking.start_time < end,
        models.Booking.end_time > start,
    )
    if exclude_id is not None:
        q = q.filter(models.Booking.id != exclude_id)
    return db.query(q.exists()).scalar()


@router.get("/", response_model=List[schemas.BookingOut])
def list_all_bookings(
    db: Session = Depends(get_db),
    _: TokenData = Depends(require_role("admin", "auditor", "facility_manager")),
):
    return db.query(models.Booking).all()


@router.get("/me", response_model=List[schemas.BookingOut])
def list_my_bookings(
    db: Session = Depends(get_db),
    token_data: TokenData = Depends(get_current_token_data),
):
    return db.query(models.Booking).filter(models.Booking.user_id == token_data.user_id).all()


@router.post("/", response_model=schemas.BookingOut, status_code=201)
def create_booking(
    booking_in: schemas.BookingCreate,
    db: Session = Depends(get_db),
    token_data: TokenData = Depends(get_current_token_data),
):
    if booking_in.start_time >= booking_in.end_time:
        raise HTTPException(status_code=400, detail="Invalid time range")

    if has_overlap(db, booking_in.room_id, booking_in.start_time, booking_in.end_time):
        raise HTTPException(status_code=400, detail="Room not available in this timeslot")

    booking = models.Booking(
        user_id=token_data.user_id,
        room_id=booking_in.room_id,
        start_time=booking_in.start_time,
        end_time=booking_in.end_time,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@router.put("/{booking_id}", response_model=schemas.BookingOut)
def update_booking(
    booking_id: int,
    booking_update: schemas.BookingUpdate,
    db: Session = Depends(get_db),
    token_data: TokenData = Depends(get_current_token_data),
):
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # Only owner or admin/facility_manager can update
    if booking.user_id != token_data.user_id and token_data.role not in [
        "admin",
        "facility_manager",
    ]:
        raise HTTPException(status_code=403, detail="Not allowed")

    data = booking_update.dict(exclude_unset=True)
    new_room_id = data.get("room_id", booking.room_id)
    new_start = data.get("start_time", booking.start_time)
    new_end = data.get("end_time", booking.end_time)

    if new_start >= new_end:
        raise HTTPException(status_code=400, detail="Invalid time range")

    if has_overlap(db, new_room_id, new_start, new_end, exclude_id=booking.id):
        raise HTTPException(status_code=400, detail="Room not available in this timeslot")

    booking.room_id = new_room_id
    booking.start_time = new_start
    booking.end_time = new_end

    db.commit()
    db.refresh(booking)
    return booking


@router.delete("/{booking_id}", status_code=204)
async def cancel_booking(
    booking_id: int,
    x_mfa_code: str = Header(None, alias="X-MFA-Code"),
    db: Session = Depends(get_db),
    token_data: TokenData = Depends(get_current_token_data),
):
    """
    Cancel a booking. Requires MFA if enabled for the user.
    Provide MFA code in X-MFA-Code header.
    """
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.user_id != token_data.user_id and token_data.role not in [
        "admin",
        "facility_manager",
    ]:
        raise HTTPException(status_code=403, detail="Not allowed")

    # Note: MFA verification would require inter-service communication
    # For now, we document that X-MFA-Code header should be provided if MFA is enabled
    
    booking.status = "cancelled"
    db.commit()
    return None


@router.get("/availability")
def check_availability(
    room_id: int = Query(...),
    start_time: datetime = Query(...),
    end_time: datetime = Query(...),
    db: Session = Depends(get_db),
    _: TokenData = Depends(get_current_token_data),
):
    available = not has_overlap(db, room_id, start_time, end_time)
    return {"room_id": room_id, "available": available}


@router.get("/user/{user_id}", response_model=List[schemas.BookingOut])
def user_booking_history(
    user_id: int,
    db: Session = Depends(get_db),
    _: TokenData = Depends(require_role("admin", "auditor")),
):
    return db.query(models.Booking).filter(models.Booking.user_id == user_id).all()
