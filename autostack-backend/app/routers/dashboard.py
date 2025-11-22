from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import Deployment, Project, User
from ..schemas import DashboardStats, DashboardStatsResponse, RecentDeploymentItem
from ..security import get_current_user


router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _format_duration(seconds: int | None) -> str | None:
    if seconds is None:
        return None
    minutes, sec = divmod(seconds, 60)
    if minutes:
        return f"{minutes}m {sec}s"
    return f"{sec}s"


def _format_time(dt: datetime | None) -> str:
    if not dt:
        return datetime.utcnow().isoformat() + "Z"
    return dt.isoformat() + "Z"


@router.get("/stats", response_model=DashboardStatsResponse)
async def dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardStatsResponse:
    # Total deployments for user (excluding soft-deleted)
    total_q = select(func.count()).select_from(Deployment).where(
        Deployment.user_id == current_user.id, Deployment.is_deleted.is_(False)
    )
    total = (await db.execute(total_q)).scalar_one()

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_q = select(func.count()).select_from(Deployment).where(
        Deployment.user_id == current_user.id,
        Deployment.is_deleted.is_(False),
        Deployment.created_at >= today_start,
    )
    today_count = (await db.execute(today_q)).scalar_one()

    success_q = select(func.count()).select_from(Deployment).where(
        Deployment.user_id == current_user.id,
        Deployment.is_deleted.is_(False),
        Deployment.status == "success",
    )
    success_count = (await db.execute(success_q)).scalar_one()

    avg_time_q = select(func.avg(Deployment.build_duration_seconds)).where(
        Deployment.user_id == current_user.id,
        Deployment.is_deleted.is_(False),
        Deployment.build_duration_seconds.is_not(None),
    )
    avg_seconds = (await db.execute(avg_time_q)).scalar_one()

    success_rate = float(success_count) / float(total) * 100 if total else 0.0
    avg_deploy_time = _format_duration(int(avg_seconds)) if avg_seconds is not None else "0s"

    # Active projects = number of distinct projects that have at least one non-deleted deployment
    active_projects_q = (
        select(func.count(func.distinct(Deployment.project_id)))
        .where(Deployment.user_id == current_user.id, Deployment.is_deleted.is_(False))
    )
    active_projects = (await db.execute(active_projects_q)).scalar_one()

    stats = DashboardStats(
        total_deployments=total,
        weekly_change="+0",  # placeholder for MVP
        active_projects=active_projects,
        today_deployments=today_count,
        success_rate=round(success_rate, 2),
        monthly_success_change=0.0,
        avg_deploy_time=avg_deploy_time or "0s",
        time_improvement="-0s",
    )

    # Recent deployments (max 5)
    recent_query = (
        select(Deployment, Project)
        .join(Project, Deployment.project_id == Project.id)
        .where(Deployment.user_id == current_user.id, Deployment.is_deleted.is_(False))
        .order_by(Deployment.created_at.desc())
        .limit(5)
    )
    result = await db.execute(recent_query)
    rows = result.all()

    recent_items: list[RecentDeploymentItem] = []
    for dep, project in rows:
        recent_items.append(
            RecentDeploymentItem(
                id=str(dep.id),
                name=project.name,
                repo=project.repository,
                branch=dep.branch or project.branch,
                status=dep.status,
                author=dep.author,
                commit=dep.commit_hash,
                commit_message=dep.commit_message,
                duration=_format_duration(dep.build_duration_seconds),
                time=_format_time(dep.created_at),
                timestamp=dep.created_at,
                url=dep.deployed_url,
                creator_type=dep.creator_type,
                is_production=dep.is_production,
            )
        )

    return DashboardStatsResponse(stats=stats, recent_deployments=recent_items)
