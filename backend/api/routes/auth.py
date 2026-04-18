"""JWT authentication endpoints."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status
from jose import jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from backend.config import get_settings

router = APIRouter()
settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Lazily hashed on first access to avoid import-time bcrypt errors
_DEMO_USERS_PLAIN: dict[str, str] = {"admin": "admin1234"}
_DEMO_USERS_HASHED: dict[str, str] = {}


def _get_hashed(username: str) -> str | None:
    plain = _DEMO_USERS_PLAIN.get(username)
    if plain is None:
        return None
    if username not in _DEMO_USERS_HASHED:
        _DEMO_USERS_HASHED[username] = pwd_context.hash(plain)
    return _DEMO_USERS_HASHED[username]


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


def _create_token(sub: str, expires_delta: timedelta, token_type: str = "access") -> str:
    expire = datetime.now(timezone.utc) + expires_delta
    payload = {"sub": sub, "exp": expire, "type": token_type}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest) -> TokenResponse:
    hashed = _get_hashed(body.username)
    if not hashed or not pwd_context.verify(body.password, hashed):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    access = _create_token(
        body.username,
        timedelta(minutes=settings.jwt_access_expire_minutes),
        "access",
    )
    refresh = _create_token(
        body.username,
        timedelta(days=settings.jwt_refresh_expire_days),
        "refresh",
    )
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest) -> TokenResponse:
    from jose import JWTError

    try:
        payload = jwt.decode(body.refresh_token, settings.secret_key, algorithms=["HS256"])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        username: str = payload["sub"]
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    access = _create_token(
        username,
        timedelta(minutes=settings.jwt_access_expire_minutes),
        "access",
    )
    new_refresh = _create_token(
        username,
        timedelta(days=settings.jwt_refresh_expire_days),
        "refresh",
    )
    return TokenResponse(access_token=access, refresh_token=new_refresh)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout() -> None:
    # Token invalidation would require a Redis blacklist in production.
    # For now, clients simply discard the token.
    return None
