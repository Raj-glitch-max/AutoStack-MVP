from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..db import get_db
from ..errors import ApiError
from ..models import Deployment, DeploymentContainer
from ..security import get_current_user
from ..services.container_runtime import (
    get_container_logs,
    is_docker_available,
    latest_container,
    record_health_check,
    start_container,
    stop_container,
)
from ..schemas import DeploymentLogsResponse, MessageResponse


router = APIRouter(prefix="/api/deployments", tags=["deployments-runtime"])


async def _get_owned_deployment(
    db: AsyncSession,
    user_id: uuid.UUID,
    deployment_id: str,
) -> Deployment:
    try:
        dep_uuid = uuid.UUID(deployment_id)
    except ValueError:
        raise ApiError("NOT_FOUND", "Deployment not found", 404)

    result = await db.execute(
        select(Deployment).where(Deployment.id == dep_uuid, Deployment.user_id == user_id, Deployment.is_deleted.is_(False))
    )
    deployment = result.scalar_one_or_none()
    if not deployment:
        raise ApiError("NOT_FOUND", "Deployment not found", 404)
    return deployment


@router.post("/{deployment_id}/runtime/start")
async def start_runtime(
    deployment_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    deployment = await _get_owned_deployment(db, current_user.id, deployment_id)

    if deployment.status != "success":
        raise ApiError("INVALID_STATE", "Deployment is not successful", 409)

    if not settings.docker_enable:
        raise ApiError("RUNTIME_DISABLED", "Docker runtime is disabled", 400)

    if not is_docker_available():
        raise ApiError("RUNTIME_UNAVAILABLE", "Docker is not installed or not accessible", 400)

    existing = await latest_container(db, deployment.id)
    if existing and existing.status in {"starting", "running"}:
        raise ApiError("CONFLICT", "Runtime container already running for this deployment", 409)

    artifacts_dir = settings.autostack_deploy_dir.rstrip("/\\") + f"/{deployment.id}"

    container = await start_container(db, deployment, Path(artifacts_dir))

    # Perform an immediate health check against the container URL
    url = f"http://{container.host}:{container.port}/"
    hc = await record_health_check(db, deployment, url)
    container.status = "running" if hc.is_live else "failed"
    if hc.is_live:
        deployment.deployed_url = url
    await db.flush()
    await db.commit()

    return {
        "containerId": container.container_id,
        "host": container.host,
        "port": container.port,
        "url": deployment.deployed_url,
        "status": container.status,
    }


@router.post("/{deployment_id}/runtime/stop", response_model=MessageResponse)
async def stop_runtime(
    deployment_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    deployment = await _get_owned_deployment(db, current_user.id, deployment_id)

    container = await latest_container(db, deployment.id)
    if not container:
        raise ApiError("NOT_FOUND", "No runtime container for this deployment", 404)

    await stop_container(db, container)
    await db.commit()

    return MessageResponse()


@router.post("/{deployment_id}/runtime/redeploy", response_model=MessageResponse)
async def redeploy_runtime(
    deployment_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    deployment = await _get_owned_deployment(db, current_user.id, deployment_id)

    container = await latest_container(db, deployment.id)
    if container:
        await stop_container(db, container)

    # For now, redeploy means restart runtime container using existing artifacts.
    # The build pipeline has already produced artifacts; we reuse them.
    if not settings.docker_enable or not is_docker_available():
        raise ApiError("RUNTIME_UNAVAILABLE", "Docker runtime is disabled or not installed", 400)

    artifacts_dir = settings.autostack_deploy_dir.rstrip("/\\") + f"/{deployment.id}"
    container = await start_container(db, deployment, Path(artifacts_dir))
    url = f"http://{container.host}:{container.port}/"
    hc = await record_health_check(db, deployment, url)
    container.status = "running" if hc.is_live else "failed"
    if hc.is_live:
        deployment.deployed_url = url
    await db.flush()
    await db.commit()

    return MessageResponse()


@router.get("/{deployment_id}/status-page")
async def deployment_status_page(
    deployment_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    deployment = await _get_owned_deployment(db, current_user.id, deployment_id)
    if not deployment.deployed_url:
        raise ApiError("INVALID_STATE", "Deployment has no deployed URL", 400)

    hc = await record_health_check(db, deployment, deployment.deployed_url)
    await db.commit()

    return {
        "url": hc.url,
        "http_status": hc.http_status,
        "latency_ms": hc.latency_ms,
        "is_live": hc.is_live,
        "checked_at": hc.checked_at.isoformat() + "Z",
    }


@router.get("/{deployment_id}/logs/runtime", response_model=DeploymentLogsResponse)
async def deployment_runtime_logs(
    deployment_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DeploymentLogsResponse:
    deployment = await _get_owned_deployment(db, current_user.id, deployment_id)

    container = await latest_container(db, deployment.id)
    if not container:
        raise ApiError("NOT_FOUND", "No runtime container for this deployment", 404)

    lines = await get_container_logs(db, deployment, container)
    await db.commit()

    return DeploymentLogsResponse(logs=lines)


@router.get("/{deployment_id}/metrics")
async def deployment_metrics(
    deployment_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    deployment = await _get_owned_deployment(db, current_user.id, deployment_id)

    container = await latest_container(db, deployment.id)
    uptime_seconds: int | None = None
    container_status: str | None = None

    if container:
        container_status = container.status
        end_time = container.stopped_at or datetime.utcnow()
        uptime_seconds = int((end_time - container.created_at).total_seconds())

    # Last health check
    from ..models import DeploymentHealthCheck  # local import to avoid circular

    result = await db.execute(
        select(DeploymentHealthCheck)
        .where(DeploymentHealthCheck.deployment_id == deployment.id)
        .order_by(DeploymentHealthCheck.checked_at.desc())
    )
    last_hc = result.scalar_one_or_none()

    last_health = None
    if last_hc:
        last_health = {
            "url": last_hc.url,
            "http_status": last_hc.http_status,
            "latency_ms": last_hc.latency_ms,
            "is_live": last_hc.is_live,
            "checked_at": last_hc.checked_at.isoformat() + "Z",
        }

    return {
        "uptime_seconds": uptime_seconds,
        "container_status": container_status,
        "last_health": last_health,
    }
