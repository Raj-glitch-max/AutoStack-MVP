from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import User, UserPreferences as UserPreferencesModel
from ..schemas import UserPreferences, UserProfile, UserProfileUpdate
from ..security import get_current_user


router = APIRouter(prefix="/api/user", tags=["user"])


@router.get("/profile", response_model=UserProfile)
async def get_profile(current_user: User = Depends(get_current_user)) -> UserProfile:
    return UserProfile(id=str(current_user.id), name=current_user.name, email=current_user.email, avatar_url=current_user.avatar_url)


@router.put("/profile", response_model=UserProfile)
async def update_profile(
    payload: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfile:
    if payload.name is not None:
        current_user.name = payload.name
    if payload.avatar_url is not None:
        current_user.avatar_url = payload.avatar_url

    await db.flush()
    await db.commit()

    return UserProfile(id=str(current_user.id), name=current_user.name, email=current_user.email, avatar_url=current_user.avatar_url)


@router.get("/preferences", response_model=UserPreferences)
async def get_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserPreferences:
    result = await db.execute(select(UserPreferencesModel).where(UserPreferencesModel.user_id == current_user.id))
    prefs = result.scalar_one_or_none()
    if not prefs:
        prefs = UserPreferencesModel(user_id=current_user.id)
        db.add(prefs)
        await db.flush()
        await db.commit()
    return UserPreferences(
        theme=prefs.theme,
        email_notifications=prefs.email_notifications,
        deployment_success_notifications=prefs.deployment_success_notifications,
        deployment_failure_notifications=prefs.deployment_failure_notifications,
    )


@router.put("/preferences", response_model=UserPreferences)
async def update_preferences(
    payload: UserPreferences,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserPreferences:
    result = await db.execute(select(UserPreferencesModel).where(UserPreferencesModel.user_id == current_user.id))
    prefs = result.scalar_one_or_none()
    if not prefs:
        prefs = UserPreferencesModel(user_id=current_user.id)
        db.add(prefs)

    prefs.theme = payload.theme
    prefs.email_notifications = payload.email_notifications
    prefs.deployment_success_notifications = payload.deployment_success_notifications
    prefs.deployment_failure_notifications = payload.deployment_failure_notifications

    await db.flush()
    await db.commit()

    return payload
