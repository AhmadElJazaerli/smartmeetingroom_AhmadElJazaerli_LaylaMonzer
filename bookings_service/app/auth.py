from jose import jwt, JWTError
from pydantic import BaseModel
from typing import Optional
from .config import settings


class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[int] = None
    role: Optional[str] = None


def decode_access_token(token: str) -> TokenData | None:
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        return TokenData(
            username=payload.get("sub"),
            user_id=payload.get("user_id"),
            role=payload.get("role"),
        )
    except JWTError:
        return None
