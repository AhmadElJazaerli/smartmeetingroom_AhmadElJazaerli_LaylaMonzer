from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from common import auth
from common.config import get_settings
from common.database import Base, engine, get_db
from common.dependencies import get_current_active_user
from common.logging_middleware import add_audit_middleware
from common.models import Booking, RoleEnum, User
from common.rate_limit import apply_rate_limiter, limiter
from common.schemas import Token, UserCreate, UserRead, UserUpdate

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.run_db_migrations:
        Base.metadata.create_all(bind=engine)
    yield


def create_app() -> FastAPI:
    fastapi_app = FastAPI(title="Users Service", version="0.2.0", lifespan=lifespan)
    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    apply_rate_limiter(fastapi_app)
    add_audit_middleware(fastapi_app, "users")
    return fastapi_app


app = create_app()


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "users"}


@app.post("/users/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register_user(request: Request, user_in: UserCreate, db: Session = Depends(get_db)) -> User:
    if db.query(User).filter((User.username == user_in.username) | (User.email == user_in.email)).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username or email already exists")

    target_role = user_in.role
    admins_exist = db.query(User).filter(User.role == RoleEnum.ADMIN).first() is not None
    if target_role != RoleEnum.REGULAR and admins_exist:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can assign elevated roles")

    hashed_password = auth.get_password_hash(user_in.password)
    user = User(
        name=user_in.name,
        username=user_in.username,
        email=user_in.email,
        role=target_role if target_role == RoleEnum.REGULAR or not admins_exist else RoleEnum.REGULAR,
        hashed_password=hashed_password,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/users/login", response_model=Token)
@limiter.limit("10/minute")
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> Token:
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")

    access_token = auth.create_access_token({"sub": user.username, "role": user.role.value})
    return Token(access_token=access_token)


@app.get("/users", response_model=list[UserRead])
@limiter.limit("20/minute")
def list_users(request: Request, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)) -> list[User]:
    if current_user.role not in {RoleEnum.ADMIN}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admins only")
    return db.query(User).all()


@app.get("/users/{username}", response_model=UserRead)
@limiter.limit("30/minute")
def get_user(
    request: Request,
    username: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> User:
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if current_user.role not in {RoleEnum.ADMIN} and current_user.username != username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return user


@app.put("/users/{username}", response_model=UserRead)
@limiter.limit("10/minute")
def update_user(
    request: Request,
    username: str,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> User:
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if current_user.role not in {RoleEnum.ADMIN} and current_user.username != username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if user_update.name:
        user.name = user_update.name
    if user_update.email:
        user.email = user_update.email
    if user_update.role and current_user.role == RoleEnum.ADMIN:
        user.role = user_update.role
    if user_update.password:
        user.hashed_password = auth.get_password_hash(user_update.password)

    db.commit()
    db.refresh(user)
    return user


@app.delete("/users/{username}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/minute")
def delete_user(
    request: Request,
    username: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> None:
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if current_user.role not in {RoleEnum.ADMIN} and current_user.username != username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    db.delete(user)
    db.commit()


@app.get("/users/{username}/bookings", response_model=list[dict])
@limiter.limit("30/minute")
def user_booking_history(
    request: Request,
    username: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if current_user.role not in {RoleEnum.ADMIN} and current_user.username != username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    bookings = (
        db.query(Booking)
        .filter(Booking.user_id == user.id)
        .order_by(Booking.start_time.desc())
        .all()
    )
    return [
        {
            "room_id": booking.room_id,
            "start_time": booking.start_time,
            "end_time": booking.end_time,
            "status": booking.status,
        }
        for booking in bookings
    ]
