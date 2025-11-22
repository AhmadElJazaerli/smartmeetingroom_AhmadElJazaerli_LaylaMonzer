from typing import List

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas
from ..deps import get_current_user, require_role, require_mfa_for_sensitive_operations

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=List[schemas.UserOut])
def list_users(
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_role("admin", "auditor")),
):
    return db.query(models.User).all()


@router.get("/{username}", response_model=schemas.UserOut)
def get_user_by_username(
    username: str,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_role("admin", "auditor")),
):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/me/profile", response_model=schemas.UserOut)
def get_me(current_user: models.User = Depends(get_current_user)):
    return current_user


@router.put("/me/profile", response_model=schemas.UserOut)
def update_my_profile(
    user_update: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if user_update.name is not None:
        current_user.name = user_update.name
    if user_update.email is not None:
        current_user.email = user_update.email
    # role update only allowed to admins via a separate endpoint in future
    db.commit()
    db.refresh(current_user)
    return current_user


@router.delete("/{username}", status_code=204)
def delete_user(
    username: str,
    x_mfa_code: str = Header(None, alias="X-MFA-Code"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("admin")),
):
    """
    Delete a user. Requires MFA if enabled for the admin user.
    Provide MFA code in X-MFA-Code header.
    """
    # Verify MFA if enabled
    require_mfa_for_sensitive_operations(mfa_code=x_mfa_code, current_user=current_user)
    
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return None
