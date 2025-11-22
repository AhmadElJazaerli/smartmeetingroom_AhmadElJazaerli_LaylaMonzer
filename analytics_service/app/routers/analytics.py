from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, cast, Date
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from ..database import get_db
from ..deps import get_current_token_data, require_role
from ..auth import TokenData

router = APIRouter(prefix="/analytics", tags=["analytics"])


# Import models from other services (they share same DB)
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, CheckConstraint
from ..database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    role = Column(String)
    is_active = Column(Boolean, default=True)


class Room(Base):
    __tablename__ = "rooms"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    capacity = Column(Integer)
    equipment = Column(Text)
    location = Column(String)
    is_available = Column(Boolean, default=True)
    is_out_of_service = Column(Boolean, default=False)


class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    room_id = Column(Integer)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    status = Column(String, default="confirmed")
    created_at = Column(DateTime, default=datetime.utcnow)


class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    room_id = Column(Integer)
    rating = Column(Integer)
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


@router.get("/dashboard/overview")
def get_dashboard_overview(
    db: Session = Depends(get_db),
    _: TokenData = Depends(require_role("admin", "auditor", "facility_manager")),
):
    """
    Get overview statistics for the main dashboard.
    Includes total counts and recent activity.
    """
    # Total counts
    total_users = db.query(func.count(User.id)).scalar()
    active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar()
    total_rooms = db.query(func.count(Room.id)).scalar()
    available_rooms = db.query(func.count(Room.id)).filter(
        Room.is_available == True, Room.is_out_of_service == False
    ).scalar()
    
    # Booking statistics
    total_bookings = db.query(func.count(Booking.id)).scalar()
    confirmed_bookings = db.query(func.count(Booking.id)).filter(
        Booking.status == "confirmed"
    ).scalar()
    
    # Today's bookings
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    todays_bookings = db.query(func.count(Booking.id)).filter(
        and_(
            Booking.start_time >= today_start,
            Booking.start_time < today_end,
            Booking.status == "confirmed"
        )
    ).scalar()
    
    # Review statistics
    total_reviews = db.query(func.count(Review.id)).scalar()
    avg_rating = db.query(func.avg(Review.rating)).scalar() or 0.0
    
    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "inactive": total_users - active_users
        },
        "rooms": {
            "total": total_rooms,
            "available": available_rooms,
            "unavailable": total_rooms - available_rooms
        },
        "bookings": {
            "total": total_bookings,
            "confirmed": confirmed_bookings,
            "cancelled": total_bookings - confirmed_bookings,
            "today": todays_bookings
        },
        "reviews": {
            "total": total_reviews,
            "average_rating": round(float(avg_rating), 2)
        }
    }


@router.get("/bookings/frequency")
def get_booking_frequency(
    period: str = "daily",  # daily, weekly, monthly
    days: int = 30,
    db: Session = Depends(get_db),
    _: TokenData = Depends(require_role("admin", "auditor", "facility_manager")),
):
    """
    Get booking frequency over time.
    Period can be: daily, weekly, monthly
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    bookings = db.query(
        cast(Booking.created_at, Date).label("date"),
        func.count(Booking.id).label("count")
    ).filter(
        and_(
            Booking.created_at >= start_date,
            Booking.created_at <= end_date
        )
    ).group_by(cast(Booking.created_at, Date)).order_by(cast(Booking.created_at, Date)).all()
    
    return {
        "period": period,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "data": [
            {
                "date": booking.date.isoformat(),
                "count": booking.count
            }
            for booking in bookings
        ]
    }


@router.get("/bookings/by-room")
def get_bookings_by_room(
    days: int = 30,
    db: Session = Depends(get_db),
    _: TokenData = Depends(require_role("admin", "auditor", "facility_manager")),
):
    """
    Get booking count by room for the specified period.
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    room_bookings = db.query(
        Room.id,
        Room.name,
        func.count(Booking.id).label("booking_count")
    ).outerjoin(
        Booking,
        and_(
            Booking.room_id == Room.id,
            Booking.created_at >= start_date,
            Booking.created_at <= end_date
        )
    ).group_by(Room.id, Room.name).order_by(func.count(Booking.id).desc()).all()
    
    return {
        "period_days": days,
        "data": [
            {
                "room_id": rb.id,
                "room_name": rb.name,
                "booking_count": rb.booking_count
            }
            for rb in room_bookings
        ]
    }


@router.get("/bookings/by-user")
def get_bookings_by_user(
    days: int = 30,
    limit: int = 10,
    db: Session = Depends(get_db),
    _: TokenData = Depends(require_role("admin", "auditor")),
):
    """
    Get top users by booking count.
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    user_bookings = db.query(
        User.id,
        User.username,
        User.name,
        func.count(Booking.id).label("booking_count")
    ).join(
        Booking,
        and_(
            Booking.user_id == User.id,
            Booking.created_at >= start_date,
            Booking.created_at <= end_date
        )
    ).group_by(User.id, User.username, User.name).order_by(
        func.count(Booking.id).desc()
    ).limit(limit).all()
    
    return {
        "period_days": days,
        "top_users": [
            {
                "user_id": ub.id,
                "username": ub.username,
                "name": ub.name,
                "booking_count": ub.booking_count
            }
            for ub in user_bookings
        ]
    }


@router.get("/rooms/ratings")
def get_room_ratings(
    db: Session = Depends(get_db),
    _: TokenData = Depends(require_role("admin", "auditor", "facility_manager")),
):
    """
    Get average ratings for all rooms with review counts.
    """
    room_ratings = db.query(
        Room.id,
        Room.name,
        Room.location,
        func.avg(Review.rating).label("avg_rating"),
        func.count(Review.id).label("review_count")
    ).outerjoin(
        Review, Review.room_id == Room.id
    ).group_by(
        Room.id, Room.name, Room.location
    ).order_by(
        func.avg(Review.rating).desc()
    ).all()
    
    return {
        "rooms": [
            {
                "room_id": rr.id,
                "room_name": rr.name,
                "location": rr.location,
                "average_rating": round(float(rr.avg_rating), 2) if rr.avg_rating else 0.0,
                "review_count": rr.review_count
            }
            for rr in room_ratings
        ]
    }


@router.get("/rooms/utilization")
def get_room_utilization(
    days: int = 30,
    db: Session = Depends(get_db),
    _: TokenData = Depends(require_role("admin", "auditor", "facility_manager")),
):
    """
    Calculate room utilization rate based on bookings.
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Get total booking hours per room
    room_usage = db.query(
        Room.id,
        Room.name,
        Room.capacity,
        func.count(Booking.id).label("booking_count"),
        func.sum(
            func.extract('epoch', Booking.end_time - Booking.start_time) / 3600
        ).label("total_hours")
    ).outerjoin(
        Booking,
        and_(
            Booking.room_id == Room.id,
            Booking.start_time >= start_date,
            Booking.start_time <= end_date,
            Booking.status == "confirmed"
        )
    ).group_by(Room.id, Room.name, Room.capacity).all()
    
    # Calculate utilization percentage (assuming 8 hours per day)
    available_hours = days * 8  # 8 working hours per day
    
    return {
        "period_days": days,
        "available_hours_per_room": available_hours,
        "rooms": [
            {
                "room_id": ru.id,
                "room_name": ru.name,
                "capacity": ru.capacity,
                "booking_count": ru.booking_count,
                "total_hours_booked": round(float(ru.total_hours or 0), 2),
                "utilization_percentage": round(
                    (float(ru.total_hours or 0) / available_hours) * 100, 2
                )
            }
            for ru in room_usage
        ]
    }


@router.get("/users/activity")
def get_user_activity(
    days: int = 30,
    db: Session = Depends(get_db),
    _: TokenData = Depends(require_role("admin", "auditor")),
):
    """
    Get user activity statistics including bookings and reviews.
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # New users registered in period
    new_users = db.query(func.count(User.id)).filter(
        User.id > 0  # Assuming auto-increment, could add created_at if available
    ).scalar()
    
    # Active users (made bookings or reviews)
    active_booking_users = db.query(func.count(func.distinct(Booking.user_id))).filter(
        and_(
            Booking.created_at >= start_date,
            Booking.created_at <= end_date
        )
    ).scalar()
    
    active_review_users = db.query(func.count(func.distinct(Review.user_id))).filter(
        and_(
            Review.created_at >= start_date,
            Review.created_at <= end_date
        )
    ).scalar()
    
    # Role distribution
    role_distribution = db.query(
        User.role,
        func.count(User.id).label("count")
    ).group_by(User.role).all()
    
    return {
        "period_days": days,
        "total_users": db.query(func.count(User.id)).scalar(),
        "active_users": {
            "made_bookings": active_booking_users,
            "made_reviews": active_review_users
        },
        "role_distribution": [
            {
                "role": rd.role,
                "count": rd.count
            }
            for rd in role_distribution
        ]
    }


@router.get("/trends/monthly")
def get_monthly_trends(
    months: int = 6,
    db: Session = Depends(get_db),
    _: TokenData = Depends(require_role("admin", "auditor", "facility_manager")),
):
    """
    Get monthly trends for bookings and reviews.
    """
    end_date = datetime.utcnow()
    start_date = end_date - relativedelta(months=months)
    
    # Monthly bookings
    monthly_bookings = db.query(
        func.date_trunc('month', Booking.created_at).label('month'),
        func.count(Booking.id).label('count')
    ).filter(
        Booking.created_at >= start_date
    ).group_by(
        func.date_trunc('month', Booking.created_at)
    ).order_by(
        func.date_trunc('month', Booking.created_at)
    ).all()
    
    # Monthly reviews
    monthly_reviews = db.query(
        func.date_trunc('month', Review.created_at).label('month'),
        func.count(Review.id).label('count'),
        func.avg(Review.rating).label('avg_rating')
    ).filter(
        Review.created_at >= start_date
    ).group_by(
        func.date_trunc('month', Review.created_at)
    ).order_by(
        func.date_trunc('month', Review.created_at)
    ).all()
    
    return {
        "period_months": months,
        "bookings": [
            {
                "month": mb.month.isoformat() if mb.month else None,
                "count": mb.count
            }
            for mb in monthly_bookings
        ],
        "reviews": [
            {
                "month": mr.month.isoformat() if mr.month else None,
                "count": mr.count,
                "average_rating": round(float(mr.avg_rating), 2)
            }
            for mr in monthly_reviews
        ]
    }


@router.get("/peak-hours")
def get_peak_hours(
    days: int = 30,
    db: Session = Depends(get_db),
    _: TokenData = Depends(require_role("admin", "auditor", "facility_manager")),
):
    """
    Get peak booking hours.
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    hourly_bookings = db.query(
        func.extract('hour', Booking.start_time).label('hour'),
        func.count(Booking.id).label('count')
    ).filter(
        and_(
            Booking.start_time >= start_date,
            Booking.start_time <= end_date,
            Booking.status == "confirmed"
        )
    ).group_by(
        func.extract('hour', Booking.start_time)
    ).order_by(
        func.count(Booking.id).desc()
    ).all()
    
    return {
        "period_days": days,
        "peak_hours": [
            {
                "hour": int(hb.hour),
                "booking_count": hb.count
            }
            for hb in hourly_bookings
        ]
    }
