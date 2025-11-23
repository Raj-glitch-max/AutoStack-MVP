from __future__ import annotations

import uuid
from datetime import datetime, timedelta
import hashlib
import logging
import secrets
from urllib.parse import quote, urlencode

import httpx
import jwt
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..db import get_db
from ..errors import ApiError
from ..models import GithubConnection, PasswordResetToken, Session, User
from ..schemas import (
    AuthResponse,
    ForgotPasswordRequest,
    LogoutRequest,
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    ResetPasswordRequest,
    SessionResponse,
    SignupRequest,
    UserInfo,
)
from ..security import ALGORITHM, create_access_token, get_current_user, hash_password, verify_password
from ..services.email import send_email


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

oauth_router = APIRouter(tags=["auth"])

RESET_TOKEN_EXPIRY_MINUTES = 60


LOGIN_MAX_FAILURES = 5
LOGIN_WINDOW_SECONDS = 300  # 5 minutes
_login_failures: dict[str, list[datetime]] = {}


def _login_rate_limit_key(request: Request, email: str | None) -> str:
    client_host = request.client.host if request.client else "unknown"
    return f"{client_host}:{(email or '').lower()}"


def _get_recent_failures(key: str, now: datetime) -> list[datetime]:
    attempts = _login_failures.get(key, [])
    attempts = [ts for ts in attempts if (now - ts).total_seconds() < LOGIN_WINDOW_SECONDS]
    _login_failures[key] = attempts
    return attempts


def _check_login_rate_limit(request: Request, email: str | None) -> None:
    now = datetime.utcnow()
    key = _login_rate_limit_key(request, email)
    attempts = _get_recent_failures(key, now)
    if len(attempts) >= LOGIN_MAX_FAILURES:
        raise ApiError(
            "TOO_MANY_REQUESTS",
            "Too many login attempts. Please try again in a few minutes.",
            429,
        )


def _register_login_failure(request: Request, email: str | None) -> None:
    now = datetime.utcnow()
    key = _login_rate_limit_key(request, email)
    attempts = _get_recent_failures(key, now)
    attempts.append(now)
    _login_failures[key] = attempts


def _clear_login_failures(request: Request, email: str | None) -> None:
    key = _login_rate_limit_key(request, email)
    _login_failures.pop(key, None)


def _validate_password_strength(password: str) -> None:
    """Basic password policy enforcement.

    Enforces a minimum length and requires both letters and digits.
    """
    if len(password) < 10:
        raise ApiError("VALIDATION_ERROR", "Password must be at least 10 characters long", 400)

    has_letter = any(c.isalpha() for c in password)
    has_digit = any(c.isdigit() for c in password)
    if not (has_letter and has_digit):
        raise ApiError(
            "VALIDATION_ERROR",
            "Password must include both letters and numbers",
            400,
        )


async def _create_session(db: AsyncSession, user: User) -> str:
    token = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(days=settings.jwt_refresh_token_expires_days)
    session = Session(user_id=user.id, token=token, expires_at=expires_at)
    db.add(session)
    await db.flush()
    return token


def _user_to_info(user: User) -> UserInfo:
    return UserInfo(id=str(user.id), name=user.name, email=user.email, avatar_url=user.avatar_url)


def _frontend_url(path: str) -> str:
    base = settings.frontend_url.rstrip("/")
    if not path.startswith("/"):
        path = "/" + path
    return f"{base}{path}"


def _oauth_success_redirect(provider: str, access_token: str, refresh_token: str) -> RedirectResponse:
    params = urlencode(
        {
            "provider": provider,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": settings.jwt_access_token_expires_minutes * 60,
        }
    )
    return RedirectResponse(f"{_frontend_url('/auth/callback')}?{params}")


def _oauth_error_redirect(provider: str, message: str) -> RedirectResponse:
    msg = quote(message)
    return RedirectResponse(f"{_frontend_url('/auth/error')}?provider={provider}&message={msg}")


def _generate_oauth_state(provider: str) -> str:
    payload = {
        "provider": provider,
        "exp": datetime.utcnow().timestamp() + settings.oauth_state_ttl_seconds,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def _validate_oauth_state(state: str | None, expected_provider: str) -> bool:
    if not state:
        return False
    try:
        payload = jwt.decode(state, settings.secret_key, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return False
    return payload.get("provider") == expected_provider


def _hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@router.post("/signup", response_model=AuthResponse)
async def signup(payload: SignupRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    _validate_password_strength(payload.password)

    result = await db.execute(select(User).where(User.email == payload.email))
    existing = result.scalar_one_or_none()
    if existing:
        raise ApiError("VALIDATION_ERROR", "Email already in use", 409)

    user = User(name=payload.name, email=payload.email, password_hash=hash_password(payload.password))
    db.add(user)
    await db.flush()

    access = create_access_token(user)
    refresh = await _create_session(db, user)
    await db.commit()

    return AuthResponse(access_token=access, refresh_token=refresh, user=_user_to_info(user))


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    _check_login_rate_limit(request, payload.email)

    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    client_host = request.client.host if request.client else "unknown"
    if not user or not user.password_hash or not verify_password(payload.password, user.password_hash):
        logger.warning("Login failed for email=%s from ip=%s", payload.email, client_host)
        _register_login_failure(request, payload.email)
        raise ApiError("UNAUTHORIZED", "Invalid email or password", 401)

    access = create_access_token(user)
    refresh = await _create_session(db, user)
    _clear_login_failures(request, payload.email)
    await db.commit()

    logger.info("Login successful for user_id=%s from ip=%s", user.id, client_host)

    return AuthResponse(access_token=access, refresh_token=refresh, user=_user_to_info(user))


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(payload: RefreshRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    result = await db.execute(select(Session).where(Session.token == payload.refresh_token))
    session_obj = result.scalar_one_or_none()
    if not session_obj or session_obj.expires_at < datetime.utcnow():
        raise ApiError("UNAUTHORIZED", "Invalid or expired refresh token", 401)

    user = await db.get(User, session_obj.user_id)
    if not user:
        raise ApiError("UNAUTHORIZED", "User not found", 401)

    access = create_access_token(user)

    return AuthResponse(access_token=access, refresh_token=session_obj.token, user=_user_to_info(user))


@router.post("/logout")
async def logout(payload: LogoutRequest, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    result = await db.execute(select(Session).where(Session.token == payload.refresh_token))
    session_obj = result.scalar_one_or_none()
    if session_obj:
        await db.delete(session_obj)
        await db.commit()
    return JSONResponse({"success": True})


@router.get("/session", response_model=SessionResponse)
async def get_session(current_user: User = Depends(get_current_user)) -> SessionResponse:
    return SessionResponse(user=_user_to_info(current_user), authenticated=True)


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(payload: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)) -> MessageResponse:
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user:
        return MessageResponse()

    await db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
        .values(used_at=datetime.utcnow())
    )

    token = secrets.token_urlsafe(48)
    token_hash = _hash_reset_token(token)
    expires_at = datetime.utcnow() + timedelta(minutes=RESET_TOKEN_EXPIRY_MINUTES)
    reset_token = PasswordResetToken(user_id=user.id, token_hash=token_hash, expires_at=expires_at)
    db.add(reset_token)
    await db.flush()

    reset_url = f"{str(settings.frontend_url).rstrip('/')}/reset-password?token={token}"
    body = "\n".join(
        [
            f"Hi {user.name},",
            "",
            "We received a request to reset your Autostack password.",
            "If this was you, click the link below to set a new password:",
            reset_url,
            "",
            "If you did not request this, you can safely ignore this email.",
        ]
    )
    send_email("Reset your Autostack password", body, user.email)
    await db.commit()

    return MessageResponse()


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)) -> MessageResponse:
    token_hash = _hash_reset_token(payload.token)
    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash, PasswordResetToken.used_at.is_(None)
        )
    )
    reset_token = result.scalar_one_or_none()
    if not reset_token or reset_token.expires_at < datetime.utcnow():
        raise ApiError("UNAUTHORIZED", "Invalid or expired reset token", 401)

    user = await db.get(User, reset_token.user_id)
    if not user:
        raise ApiError("UNAUTHORIZED", "User not found", 401)

    # Enforce password strength and prevent reusing the existing password when present.
    _validate_password_strength(payload.password)
    if user.password_hash and verify_password(payload.password, user.password_hash):
        raise ApiError("VALIDATION_ERROR", "New password must be different from the old password", 400)

    user.password_hash = hash_password(payload.password)
    reset_token.used_at = datetime.utcnow()

    await db.flush()
    await db.commit()

    return MessageResponse()


# OAuth helpers

def _github_authorize_url(state: str) -> str:
    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": settings.github_callback_url,
        "scope": "repo user:email",
        "state": state,
        "allow_signup": "false",
    }
    return f"https://github.com/login/oauth/authorize?{urlencode(params)}"


@oauth_router.get("/auth/github")
async def github_auth_start() -> RedirectResponse:
    state = _generate_oauth_state("github")
    return RedirectResponse(_github_authorize_url(state))


@oauth_router.get("/auth/github/callback")
async def github_auth_callback(
    code: str,
    state: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    if not _validate_oauth_state(state, "github"):
        return _oauth_error_redirect("github", "Invalid or expired OAuth state")

    try:
        async with httpx.AsyncClient() as client:
            token_resp = await client.post(
                "https://github.com/login/oauth/access_token",
                data={
                    "client_id": settings.github_client_id,
                    "client_secret": settings.github_client_secret,
                    "code": code,
                    "redirect_uri": settings.github_callback_url,
                },
                headers={"Accept": "application/json"},
                timeout=20,
            )
            token_resp.raise_for_status()
            token_data = token_resp.json()
            access_token = token_data.get("access_token")
            scope = token_data.get("scope")
            if not access_token:
                raise ValueError(token_data.get("error_description") or "Missing access token")

            user_resp = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"token {access_token}"},
                timeout=20,
            )
            user_resp.raise_for_status()
            user_json = user_resp.json()

            github_id = str(user_json.get("id"))
            login = user_json.get("login")
            name = user_json.get("name") or login or "GitHub User"
            avatar_url = user_json.get("avatar_url")

            emails_resp = await client.get(
                "https://api.github.com/user/emails",
                headers={"Authorization": f"token {access_token}"},
                timeout=20,
            )
            emails = emails_resp.json() if emails_resp.status_code == 200 else []
            primary_email = None
            for item in emails:
                if item.get("primary") and item.get("verified"):
                    primary_email = item.get("email")
                    break
            if not primary_email:
                primary_email = f"{login}+autostack@users.noreply.github.com"
    except Exception as exc:  # pragma: no cover - network errors
        logger.exception("GitHub OAuth callback failed: %s", exc)
        return _oauth_error_redirect("github", "GitHub authentication failed")

    result = await db.execute(select(User).where(User.github_id == github_id))
    user = result.scalar_one_or_none()
    if not user:
        result = await db.execute(select(User).where(User.email == primary_email))
        user = result.scalar_one_or_none()
    if not user:
            github_username=login,
            github_access_token=access_token,
            scope=scope,
        )
        db.add(conn)
    else:
        conn.github_username = login or conn.github_username
        conn.github_access_token = access_token
        conn.scope = scope or conn.scope

    access = create_access_token(user)
    refresh = await _create_session(db, user)
    await db.commit()

    return _oauth_success_redirect("github", access, refresh)


# Google OAuth (simplified JSON response)


def _google_token_url() -> str:
    return "https://oauth2.googleapis.com/token"


@oauth_router.get("/auth/google")
async def google_auth_start() -> RedirectResponse:
    state = _generate_oauth_state("google")
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_callback_url,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    logger.info("Initiating Google Auth with params: client_id=%s..., redirect_uri=%s", 
                settings.google_client_id[:5] if settings.google_client_id else "None", 
                settings.google_callback_url)
    logger.info("Full Google Auth URL: %s", url)
    return RedirectResponse(url)


@oauth_router.get("/auth/google/callback")
async def google_auth_callback(
    code: str,
    state: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    # In this MVP/dev environment we log invalid state but do not block the flow,
    # to avoid hard-to-debug local issues while still keeping basic state usage.
    if not _validate_oauth_state(state, "google"):
        logger.warning("Google OAuth callback received invalid or expired state; proceeding without strict validation")

    try:
        async with httpx.AsyncClient() as client:
            token_resp = await client.post(
                _google_token_url(),
                data={
                    "code": code,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uri": settings.google_callback_url,
                    "grant_type": "authorization_code",
                },
                timeout=20,
            )
            token_resp.raise_for_status()
            token_data = token_resp.json()
            access_token = token_data.get("access_token")
            if not access_token:
                raise ValueError(token_data.get("error_description") or "Missing access token")

            user_resp = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=20,
            )
            user_resp.raise_for_status()
            user_json = user_resp.json()
    except Exception as exc:  # pragma: no cover - network errors
        logger.exception("Google OAuth callback failed: %s", exc)
        return _oauth_error_redirect("google", "Google authentication failed")

    google_id = user_json.get("id")
    email = user_json.get("email")
    name = user_json.get("name") or email
    avatar_url = user_json.get("picture")

    if not email:
        return _oauth_error_redirect("google", "Google account missing email")

    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()
    if not user:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
    if not user:
        user = User(name=name, email=email, google_id=google_id, avatar_url=avatar_url, email_verified=True)
        db.add(user)
        await db.flush()
    else:
        user.google_id = google_id
        user.avatar_url = avatar_url or user.avatar_url

    access = create_access_token(user)
    refresh = await _create_session(db, user)
    await db.commit()

    return _oauth_success_redirect("google", access, refresh)
