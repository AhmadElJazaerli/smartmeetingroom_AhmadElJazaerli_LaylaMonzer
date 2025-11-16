from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext

from .config import settings
from .schemas import TokenData

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(*, user_id: int, username: str, role: str) -> str:
    to_encode = {
        "sub": username,
        "user_id": user_id,
        "role": role,
        "exp": datetime.utcnow()
        + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> TokenData | None:
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        username = payload.get("sub")
        user_id = payload.get("user_id")
        role = payload.get("role")
        if username is None or user_id is None:
            return None
        return TokenData(username=username, user_id=user_id, role=role)
    except JWTError:
        return None
