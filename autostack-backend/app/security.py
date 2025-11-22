from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .db import get_db
from .errors import ApiError
from .models import User


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"

bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user: User) -> str:
    expires_delta = timedelta(minutes=settings.jwt_access_token_expires_minutes)
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "userId": str(user.id),
        "email": user.email,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "type": "access",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise ApiError("UNAUTHORIZED", "Invalid authentication token", 401)
    return payload


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise ApiError("UNAUTHORIZED", "Not authenticated", 401)

    token = credentials.credentials
    payload = decode_token(token)

    if payload.get("type") != "access":
        raise ApiError("UNAUTHORIZED", "Invalid access token", 401)

    user_id_str = payload.get("userId")
    if not isinstance(user_id_str, str):
        raise ApiError("UNAUTHORIZED", "Invalid token payload", 401)

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise ApiError("UNAUTHORIZED", "Invalid token payload", 401)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise ApiError("UNAUTHORIZED", "User not found", 401)

    return user
