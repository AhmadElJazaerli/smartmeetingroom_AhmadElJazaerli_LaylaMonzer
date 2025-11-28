"""Reusable FastAPI dependencies for auth and database access."""
from typing import Callable, Iterable, List

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .auth import decode_token
from .config import get_settings
from .database import get_db
from .models import RoleEnum, User

settings = get_settings()
oauth_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")
service_api_key_header = APIKeyHeader(name="X-Service-Key", auto_error=False)


def get_current_user(token: str = Depends(oauth_scheme), db: Session = Depends(get_db)) -> User:
    payload = decode_token(token)
    username: str | None = payload.get("sub")
    if username is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing subject in token")
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user


def allow_roles(*roles: RoleEnum) -> Callable[[User], User]:
    def dependency(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user

    return dependency


def require_service_key(api_key: str = Security(service_api_key_header)) -> None:
    if not api_key or api_key != settings.service_api_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid service key")
