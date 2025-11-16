from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm

from ..database import get_db
from .. import models, schemas
from ..auth import get_password_hash, create_access_token
from ..deps import authenticate_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=schemas.UserOut, status_code=201)
def register_user(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = (
        db.query(models.User)
        .filter(
            (models.User.username == user_in.username)
            | (models.User.email == user_in.email)
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400, detail="Username or email already exists"
        )

    hashed_pw = get_password_hash(user_in.password)
    db_user = models.User(
        name=user_in.name,
        username=user_in.username,
        email=user_in.email,
        hashed_password=hashed_pw,
        role=user_in.role,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.post("/login", response_model=schemas.Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    access_token = create_access_token(
        user_id=user.id, username=user.username, role=user.role
    )
    return {"access_token": access_token, "token_type": "bearer"}
