from __future__ import annotations

from datetime import datetime, timedelta
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..errors import ApiError
from ..models import Deployment, DeploymentHealthCheck, Project, User
from ..schemas import (
    ProjectAnalytics,
    ProjectAnalyticsResponse,
    ProjectSettingsUpdate,
    ProjectSummary,
)
from ..security import get_current_user


router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("/by-repo", response_model=ProjectSummary)
async def get_project_by_repo(
    repository: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectSummary:
    result = await db.execute(
        select(Project).where(Project.user_id == current_user.id, Project.repository == repository)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise ApiError("NOT_FOUND", "Project not found", 404)

    return ProjectSummary(
        id=str(project.id),
        name=project.name,
        repository=project.repository,
        branch=project.branch,
        runtime=project.runtime,
        auto_deploy_enabled=project.auto_deploy_enabled,
        auto_deploy_branch=project.auto_deploy_branch,
    )


@router.post("/{project_id}/settings", response_model=ProjectSummary)
async def update_project_settings(
    project_id: str,
    payload: ProjectSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectSummary:
    try:
        proj_uuid = uuid.UUID(project_id)
    except ValueError:
        raise ApiError("NOT_FOUND", "Project not found", 404)

    project = await db.get(Project, proj_uuid)
    if not project or project.user_id != current_user.id:
        raise ApiError("NOT_FOUND", "Project not found", 404)

    if payload.auto_deploy_enabled is not None:
        project.auto_deploy_enabled = payload.auto_deploy_enabled
    if payload.auto_deploy_branch is not None and payload.auto_deploy_branch.strip():
        project.auto_deploy_branch = payload.auto_deploy_branch.strip()

    await db.flush()
    await db.commit()

    return ProjectSummary(
        id=str(project.id),
        name=project.name,
        repository=project.repository,
        branch=project.branch,
        runtime=project.runtime,
        auto_deploy_enabled=project.auto_deploy_enabled,
        auto_deploy_branch=project.auto_deploy_branch,
    )


@router.get("/{project_id}/analytics", response_model=ProjectAnalyticsResponse)
async def get_project_analytics(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectAnalyticsResponse:
    try:
        proj_uuid = uuid.UUID(project_id)
    except ValueError:
        raise ApiError("NOT_FOUND", "Project not found", 404)

    project = await db.get(Project, proj_uuid)
    if not project or project.user_id != current_user.id:
        raise ApiError("NOT_FOUND", "Project not found", 404)

    dep_query = select(Deployment).where(
        Deployment.project_id == proj_uuid,
        Deployment.is_deleted.is_(False),
    )
    dep_result = await db.execute(dep_query)
    deployments = list(dep_result.scalars().all())

    deployments_count = len(deployments)
    success_count = sum(1 for d in deployments if d.status == "success")
    failure_count = sum(1 for d in deployments if d.status == "failed")

    durations = [d.build_duration_seconds for d in deployments if d.build_duration_seconds is not None]
    avg_build_time: float | None
    if durations:
        avg_build_time = float(sum(durations) / len(durations))
    else:
        avg_build_time = None

    # Last 5 durations from most recent deployments
    recent_sorted = sorted(
        [d for d in deployments if d.build_duration_seconds is not None],
        key=lambda d: d.created_at or datetime.utcnow(),
        reverse=True,
    )
    last_5_durations = [float(d.build_duration_seconds or 0) for d in recent_sorted[:5]]

    # Uptime over the last 24 hours based on health checks
    now = datetime.utcnow()
    day_ago = now - timedelta(hours=24)

    hc_query = (
        select(DeploymentHealthCheck)
        .join(Deployment, DeploymentHealthCheck.deployment_id == Deployment.id)
        .where(
            Deployment.project_id == proj_uuid,
            DeploymentHealthCheck.checked_at >= day_ago,
        )
    )
    hc_result = await db.execute(hc_query)
    health_checks = list(hc_result.scalars().all())

    if health_checks:
        up = sum(1 for hc in health_checks if hc.is_live)
        uptime_last_24h: float | None = float(up) / float(len(health_checks)) * 100.0
    else:
        uptime_last_24h = None

    analytics = ProjectAnalytics(
        deployments_count=deployments_count,
        success_count=success_count,
        failure_count=failure_count,
        last_5_durations=last_5_durations,
        avg_build_time=avg_build_time,
        uptime_last_24h=uptime_last_24h,
    )

    return ProjectAnalyticsResponse(analytics=analytics)
