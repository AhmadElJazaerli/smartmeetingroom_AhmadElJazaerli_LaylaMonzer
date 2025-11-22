from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from .auth import decode_access_token, TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="http://localhost:8001/auth/login")


def get_current_token_data(token: str = Depends(oauth2_scheme)) -> TokenData:
    data = decode_access_token(token)
    if data is None or data.username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    return data


def require_role(*roles: str):
    def wrapper(token_data: TokenData = Depends(get_current_token_data)):
        if token_data.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return token_data

    return wrapper
