from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from ..database import get_db
from .. import models, schemas
from ..auth import get_password_hash, create_access_token
from ..deps import authenticate_user, get_current_user
from ..mfa import generate_mfa_secret, generate_totp_uri, generate_qr_code, verify_totp_code

router = APIRouter(prefix="/auth", tags=["auth"])


class MFASetupResponse(BaseModel):
    secret: str
    qr_code: str
    uri: str


class MFAVerifyRequest(BaseModel):
    code: str


class MFALoginRequest(BaseModel):
    username: str
    password: str
    mfa_code: str


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
    
    # Check if MFA is enabled
    if user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="MFA required. Use /auth/login-mfa endpoint with MFA code",
        )
    
    access_token = create_access_token(
        user_id=user.id, username=user.username, role=user.role
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login-mfa", response_model=schemas.Token)
def login_with_mfa(
    mfa_request: MFALoginRequest,
    db: Session = Depends(get_db),
):
    """Login with MFA code"""
    user = authenticate_user(db, mfa_request.username, mfa_request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    
    # Check if MFA is enabled
    if not user.mfa_enabled or not user.mfa_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not enabled for this user",
        )
    
    # Verify MFA code
    if not verify_totp_code(user.mfa_secret, mfa_request.mfa_code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MFA code",
        )
    
    access_token = create_access_token(
        user_id=user.id, username=user.username, role=user.role
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/mfa/setup", response_model=MFASetupResponse)
def setup_mfa(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Setup MFA for the current user.
    Returns QR code and secret for authenticator app.
    """
    if current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is already enabled",
        )
    
    # Generate new secret
    secret = generate_mfa_secret()
    uri = generate_totp_uri(current_user.username, secret)
    qr_code = generate_qr_code(uri)
    
    # Store secret (not enabled yet until verified)
    current_user.mfa_secret = secret
    db.commit()
    
    return {
        "secret": secret,
        "qr_code": qr_code,
        "uri": uri
    }


@router.post("/mfa/enable")
def enable_mfa(
    verify_request: MFAVerifyRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Enable MFA after verifying the setup code.
    """
    if current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is already enabled",
        )
    
    if not current_user.mfa_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA setup not initiated. Call /mfa/setup first",
        )
    
    # Verify the code
    if not verify_totp_code(current_user.mfa_secret, verify_request.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid MFA code. Please try again",
        )
    
    # Enable MFA
    current_user.mfa_enabled = True
    db.commit()
    
    return {"message": "MFA enabled successfully"}


@router.post("/mfa/disable")
def disable_mfa(
    verify_request: MFAVerifyRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Disable MFA after verifying the current code.
    """
    if not current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not enabled",
        )
    
    # Verify the code before disabling
    if not verify_totp_code(current_user.mfa_secret, verify_request.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid MFA code",
        )
    
    # Disable MFA
    current_user.mfa_enabled = False
    current_user.mfa_secret = None
    db.commit()
    
    return {"message": "MFA disabled successfully"}


@router.get("/mfa/status")
def mfa_status(current_user: models.User = Depends(get_current_user)):
    """Check if MFA is enabled for the current user"""
    return {
        "mfa_enabled": current_user.mfa_enabled,
        "username": current_user.username
    }
