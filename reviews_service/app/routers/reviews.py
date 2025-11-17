from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db
from .. import models, schemas
from ..deps import get_current_token_data, require_role
from ..auth import TokenData

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("/", response_model=List[schemas.ReviewOut])
def list_all_reviews(
    room_id: int | None = Query(None, description="Filter by room ID"),
    db: Session = Depends(get_db),
    _: TokenData = Depends(get_current_token_data),
):
    """
    List all reviews. Optionally filter by room_id.
    Accessible by authenticated users.
    """
    query = db.query(models.Review)
    if room_id is not None:
        query = query.filter(models.Review.room_id == room_id)
    return query.all()


@router.get("/room/{room_id}/stats")
def get_room_review_stats(
    room_id: int,
    db: Session = Depends(get_db),
    _: TokenData = Depends(get_current_token_data),
):
    """
    Get review statistics for a specific room.
    Returns average rating and total review count.
    """
    stats = db.query(
        func.avg(models.Review.rating).label("average_rating"),
        func.count(models.Review.id).label("total_reviews")
    ).filter(models.Review.room_id == room_id).first()
    
    return {
        "room_id": room_id,
        "average_rating": float(stats.average_rating) if stats.average_rating else 0.0,
        "total_reviews": stats.total_reviews
    }


@router.get("/me", response_model=List[schemas.ReviewOut])
def list_my_reviews(
    db: Session = Depends(get_db),
    token_data: TokenData = Depends(get_current_token_data),
):
    """
    List all reviews created by the authenticated user.
    """
    return db.query(models.Review).filter(models.Review.user_id == token_data.user_id).all()


@router.post("/", response_model=schemas.ReviewOut, status_code=201)
def create_review(
    review_in: schemas.ReviewCreate,
    db: Session = Depends(get_db),
    token_data: TokenData = Depends(get_current_token_data),
):
    """
    Create a new review for a room.
    Only authenticated users can create reviews.
    """
    # Check if user already reviewed this room
    existing = db.query(models.Review).filter(
        models.Review.user_id == token_data.user_id,
        models.Review.room_id == review_in.room_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400, 
            detail="You have already reviewed this room. Use PUT to update your review."
        )
    
    review = models.Review(
        user_id=token_data.user_id,
        room_id=review_in.room_id,
        rating=review_in.rating,
        comment=review_in.comment,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


@router.get("/{review_id}", response_model=schemas.ReviewOut)
def get_review(
    review_id: int,
    db: Session = Depends(get_db),
    _: TokenData = Depends(get_current_token_data),
):
    """
    Get a specific review by ID.
    """
    review = db.query(models.Review).filter(models.Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


@router.put("/{review_id}", response_model=schemas.ReviewOut)
def update_review(
    review_id: int,
    review_update: schemas.ReviewUpdate,
    db: Session = Depends(get_db),
    token_data: TokenData = Depends(get_current_token_data),
):
    """
    Update a review.
    Only the review owner or admin/moderator can update.
    """
    review = db.query(models.Review).filter(models.Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    # Only owner or admin/moderator can update
    if review.user_id != token_data.user_id and token_data.role not in [
        "admin",
        "moderator",
    ]:
        raise HTTPException(status_code=403, detail="Not allowed")

    data = review_update.dict(exclude_unset=True)
    for key, value in data.items():
        setattr(review, key, value)

    db.commit()
    db.refresh(review)
    return review


@router.delete("/{review_id}", status_code=204)
def delete_review(
    review_id: int,
    db: Session = Depends(get_db),
    token_data: TokenData = Depends(get_current_token_data),
):
    """
    Delete a review.
    Only the review owner or admin/moderator can delete.
    """
    review = db.query(models.Review).filter(models.Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    # Only owner or admin/moderator can delete
    if review.user_id != token_data.user_id and token_data.role not in [
        "admin",
        "moderator",
    ]:
        raise HTTPException(status_code=403, detail="Not allowed")

    db.delete(review)
    db.commit()
    return None
