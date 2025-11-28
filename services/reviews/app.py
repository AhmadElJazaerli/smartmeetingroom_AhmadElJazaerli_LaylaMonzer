from contextlib import asynccontextmanager
import html
from typing import List

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from common.config import get_settings
from common.database import Base, engine, get_db
from common.dependencies import get_current_active_user
from common.logging_middleware import add_audit_middleware
from common.models import Review, RoleEnum, Room, User
from common.rate_limit import apply_rate_limiter, limiter
from common.schemas import ReviewCreate, ReviewRead, ReviewUpdate

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.run_db_migrations:
        Base.metadata.create_all(bind=engine)
    yield


def create_app() -> FastAPI:
    fastapi_app = FastAPI(title="Reviews Service", version="0.2.0", lifespan=lifespan)
    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    apply_rate_limiter(fastapi_app)
    add_audit_middleware(fastapi_app, "reviews")
    return fastapi_app


app = create_app()


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "reviews"}


def _sanitize(comment: str) -> str:
    stripped = comment.strip()
    return html.escape(stripped)


@app.post("/reviews", response_model=ReviewRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
def submit_review(
    request: Request,
    review_in: ReviewCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Review:
    room = db.query(Room).filter(Room.id == review_in.room_id).first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    review = Review(
        user_id=current_user.id,
        room_id=review_in.room_id,
        rating=review_in.rating,
        comment=_sanitize(review_in.comment),
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


@app.put("/reviews/{review_id}", response_model=ReviewRead)
@limiter.limit("20/minute")
def update_review(
    request: Request,
    review_id: int,
    review_update: ReviewUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Review:
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    if current_user.role not in {RoleEnum.ADMIN, RoleEnum.MODERATOR} and review.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    data = review_update.model_dump(exclude_unset=True)
    if "comment" in data and data["comment"]:
        data["comment"] = _sanitize(data["comment"])

    for key, value in data.items():
        setattr(review, key, value)
    db.commit()
    db.refresh(review)
    return review


@app.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("20/minute")
def delete_review(
    request: Request,
    review_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> None:
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    if current_user.role not in {RoleEnum.ADMIN, RoleEnum.MODERATOR} and review.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    db.delete(review)
    db.commit()


@app.get("/reviews/room/{room_id}", response_model=List[ReviewRead])
@limiter.limit("60/minute")
def room_reviews(request: Request, room_id: int, db: Session = Depends(get_db)) -> List[Review]:
    return db.query(Review).filter(Review.room_id == room_id).order_by(Review.created_at.desc()).all()


@app.post("/reviews/{review_id}/flag", response_model=ReviewRead)
@limiter.limit("15/minute")
def flag_review(
    request: Request,
    review_id: int,
    action: str = "flag",
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Review:
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    if current_user.role not in {RoleEnum.ADMIN, RoleEnum.MODERATOR}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Moderators only")

    review.is_flagged = action == "flag"
    db.commit()
    db.refresh(review)
    return review
