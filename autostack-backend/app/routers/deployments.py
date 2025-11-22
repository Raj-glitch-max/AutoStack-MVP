from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..build_engine import cancel_deployment_run, enqueue_deployment
from ..db import AsyncSessionLocal, get_db
from ..errors import ApiError
from ..models import Deployment, DeploymentLog, DeploymentStage, Project, User
from ..schemas import (
    DashboardStats,
    DashboardStatsResponse,
    CommitInfo,
    DeploymentCreateRequest,
    DeploymentDetailResponse,
    DeploymentItem,
    DeploymentListResponse,
    DeploymentLogsResponse,
    DeploymentStageModel,
    Pagination,
    RecentDeploymentItem,
    RecentDeploymentsResponse,
)
from ..security import decode_token, get_current_user
from ..services.stages import order_stages, set_stage_status
from ..websockets import broadcast_deployment_event, ws_manager


router = APIRouter(prefix="/api/deployments", tags=["deployments"])


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


def _is_production_branch(project: Project, branch: str | None) -> bool:
    target = (project.auto_deploy_branch or project.branch or "main").strip()
    source = (branch or target).strip()
    if not target:
        return False
    return target.lower() == source.lower()


def _deployment_item(dep: Deployment, project: Project) -> DeploymentItem:
    return DeploymentItem(
        id=str(dep.id),
        name=project.name,
        project_id=str(project.id),
        repo=project.repository,
        branch=dep.branch or project.branch,
        status=dep.status,
        commit=dep.commit_hash,
        commit_message=dep.commit_message,
        author=dep.author,
        duration=_format_duration(dep.build_duration_seconds),
        time=_format_time(dep.created_at),
        timestamp=dep.created_at,
        url=dep.deployed_url,
        creator_type=dep.creator_type,
        is_production=dep.is_production,
        failed_reason=dep.failed_reason,
    )


@router.post("", response_model=DeploymentDetailResponse)
async def create_deployment(
    payload: DeploymentCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DeploymentDetailResponse:
    # Find or create project
    result = await db.execute(
        select(Project).where(
            Project.user_id == current_user.id,
            Project.repository == payload.repository,
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        project = Project(
            user_id=current_user.id,
            name=payload.repository,
            repository=payload.repository,
            branch=payload.branch,
            build_command=payload.build_command,
            output_dir=payload.output_dir,
            env_vars=payload.env_vars,
            runtime=(payload.runtime or "static"),
            auto_deploy_enabled=payload.auto_deploy_enabled or False,
            auto_deploy_branch=payload.auto_deploy_branch or payload.branch,
        )
        db.add(project)
        await db.flush()
    else:
        project.branch = payload.branch
        project.build_command = payload.build_command
        project.output_dir = payload.output_dir
        project.env_vars = payload.env_vars
        if payload.runtime is not None:
            project.runtime = payload.runtime
        if payload.auto_deploy_enabled is not None:
            project.auto_deploy_enabled = payload.auto_deploy_enabled
        if payload.auto_deploy_branch:
            project.auto_deploy_branch = payload.auto_deploy_branch
        elif payload.auto_deploy_enabled:
            project.auto_deploy_branch = payload.branch

    deployment = Deployment(
        project_id=project.id,
        user_id=current_user.id,
        status="queued",
        branch=payload.branch,
        creator_type="manual",
        is_production=_is_production_branch(project, payload.branch),
        env_vars=payload.env_vars or project.env_vars,
        created_at=datetime.utcnow(),
    )
    db.add(deployment)
    await db.flush()
    await set_stage_status(db, deployment.id, "queued", "in_progress")
    await db.commit()

    await enqueue_deployment(deployment.id)

    return DeploymentDetailResponse(
        id=str(deployment.id),
        project_id=str(project.id),
        name=project.name,
        repo=project.repository,
        branch=deployment.branch or project.branch,
        status=deployment.status,
        time=_format_time(deployment.created_at),
        url=deployment.deployed_url,
        commit=CommitInfo(
            sha=deployment.commit_hash,
            message=deployment.commit_message,
            author=deployment.author,
            timestamp=deployment.commit_timestamp,
        ),
        duration=_format_duration(deployment.build_duration_seconds),
        creator_type=deployment.creator_type,
        is_production=deployment.is_production,
        env_vars=deployment.env_vars,
        stages=[],
        logs=[],
        failed_reason=deployment.failed_reason,
    )


@router.get("", response_model=DeploymentListResponse)
async def list_deployments(
    search: str | None = None,
    status: str | None = Query(None, description="all, success, failed, building, queued, copying"),
    page: int = 1,
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DeploymentListResponse:
    if page < 1:
        page = 1
    if limit < 1:
        limit = 10

    query = (
        select(Deployment, Project)
        .join(Project, Deployment.project_id == Project.id)
        .where(Deployment.user_id == current_user.id, Deployment.is_deleted.is_(False))
    )

    if search:
        like = f"%{search}%"
        query = query.where(Project.name.ilike(like))

    if status and status != "all":
        query = query.where(Deployment.status == status)

    total_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(total_query)).scalar_one()

    query = query.order_by(Deployment.created_at.desc()).offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    rows = result.all()

    deployments: list[DeploymentItem] = [_deployment_item(dep, project) for dep, project in rows]

    total_pages = (total + limit - 1) // limit if total else 1

    return DeploymentListResponse(
        deployments=deployments,
        pagination=Pagination(current_page=page, total_pages=total_pages, total_items=total),
    )


@router.get("/recent", response_model=RecentDeploymentsResponse)
async def recent_deployments(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 5,
) -> RecentDeploymentsResponse:
    query = (
        select(Deployment, Project)
        .join(Project, Deployment.project_id == Project.id)
        .where(Deployment.user_id == current_user.id, Deployment.is_deleted.is_(False))
        .order_by(Deployment.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    rows = result.all()

    items: list[RecentDeploymentItem] = [
        RecentDeploymentItem(**_deployment_item(dep, project).model_dump()) for dep, project in rows
    ]

    return RecentDeploymentsResponse(recent_deployments=items)


@router.get("/{deployment_id}", response_model=DeploymentDetailResponse)
async def get_deployment(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DeploymentDetailResponse:
    try:
        dep_uuid = uuid.UUID(deployment_id)
    except ValueError:
        raise ApiError("NOT_FOUND", "Deployment not found", 404)

    result = await db.execute(
        select(Deployment, Project)
        .join(Project, Deployment.project_id == Project.id)
        .where(
            Deployment.id == dep_uuid,
            Deployment.user_id == current_user.id,
            Deployment.is_deleted.is_(False),
        )
    )
    row = result.first()
    if not row:
        raise ApiError("NOT_FOUND", "Deployment not found", 404)

    dep, project = row

    logs_result = await db.execute(
        select(DeploymentLog).where(DeploymentLog.deployment_id == dep.id).order_by(DeploymentLog.timestamp.asc())
    )
    logs = [log.message for log in logs_result.scalars().all()]

    stages_result = await db.execute(
        select(DeploymentStage).where(DeploymentStage.deployment_id == dep.id).order_by(DeploymentStage.created_at.asc())
    )
    stage_models: list[DeploymentStageModel] = []
    for stage in order_stages(stages_result.scalars().all()):
        stage_models.append(
            DeploymentStageModel(
                name=stage.stage_name,
                status=stage.status,
                timestamp=stage.started_at or stage.created_at,
                started_at=stage.started_at or stage.created_at,
                completed_at=stage.completed_at,
            )
        )

    return DeploymentDetailResponse(
        id=str(dep.id),
        project_id=str(project.id),
        name=project.name,
        repo=project.repository,
        branch=dep.branch or project.branch,
        status=dep.status,
        time=_format_time(dep.created_at),
        url=dep.deployed_url,
        commit=CommitInfo(
            sha=dep.commit_hash,
            message=dep.commit_message,
            author=dep.author,
            timestamp=dep.commit_timestamp,
        ),
        duration=_format_duration(dep.build_duration_seconds),
        creator_type=dep.creator_type,
        is_production=dep.is_production,
        env_vars=dep.env_vars,
        stages=stage_models,
        logs=logs,
        failed_reason=dep.failed_reason,
    )


@router.get("/{deployment_id}/logs", response_model=DeploymentLogsResponse)
async def get_deployment_logs(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DeploymentLogsResponse:
    try:
        dep_uuid = uuid.UUID(deployment_id)
    except ValueError:
        raise ApiError("NOT_FOUND", "Deployment not found", 404)

    dep = await db.get(Deployment, dep_uuid)
    if not dep or dep.user_id != current_user.id or dep.is_deleted:
        raise ApiError("NOT_FOUND", "Deployment not found", 404)

    logs_result = await db.execute(
        select(DeploymentLog).where(DeploymentLog.deployment_id == dep.id).order_by(DeploymentLog.timestamp.asc())
    )
    logs = [log.message for log in logs_result.scalars().all()]
    return DeploymentLogsResponse(logs=logs)


@router.post("/{deployment_id}/cancel")
async def cancel_deployment(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    try:
        dep_uuid = uuid.UUID(deployment_id)
    except ValueError:
        raise ApiError("NOT_FOUND", "Deployment not found", 404)

    dep = await db.get(Deployment, dep_uuid)
    if not dep or dep.user_id != current_user.id:
        raise ApiError("NOT_FOUND", "Deployment not found", 404)

    await cancel_deployment_run(dep.id)
    dep.status = "cancelled"
    dep.failed_reason = "Cancelled by user"
    await db.flush()
    await set_stage_status(db, dep.id, "cancelled", "completed")
    await db.commit()

    await broadcast_deployment_event(dep.id, {"type": "status_update", "status": "cancelled", "stage": "Cancelled"})

    return {"success": True}


@router.post("/{deployment_id}/delete")
async def delete_deployment(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    try:
        dep_uuid = uuid.UUID(deployment_id)
    except ValueError:
        raise ApiError("NOT_FOUND", "Deployment not found", 404)

    dep = await db.get(Deployment, dep_uuid)
    if not dep or dep.user_id != current_user.id:
        raise ApiError("NOT_FOUND", "Deployment not found", 404)

    # Stop and remove any running containers for this deployment
    from ..services.container_runtime import latest_container, stop_container, is_docker_available
    
    if is_docker_available():
        container = await latest_container(db, dep.id)
        if container and container.status == "running":
            try:
                await stop_container(db, container)
            except Exception:
                # Continue with deletion even if container stop fails
                pass

    # Soft delete: flag is_deleted (column added in model)
    from ..models import Deployment as DeploymentModel  # type: ignore

    dep.is_deleted = True  # type: ignore[attr-defined]
    await db.flush()
    await db.commit()

    return {"success": True}


@router.websocket("/{deployment_id}/logs/stream")
async def deployment_logs_stream(websocket: WebSocket, deployment_id: str, token: str = Query("")) -> None:
    if not token:
        await websocket.close(code=4401)
        return

    try:
        payload = decode_token(token)
        user_id = payload.get("userId")
        if not isinstance(user_id, str):
            await websocket.close(code=4401)
            return
    except ApiError:
        await websocket.close(code=4401)
        return

    try:
        dep_uuid = uuid.UUID(deployment_id)
    except ValueError:
        await websocket.close(code=4404)
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Deployment).where(Deployment.id == dep_uuid))
        deployment = result.scalar_one_or_none()
        if not deployment or deployment.is_deleted or str(deployment.user_id) != user_id:
            await websocket.close(code=4403)
            return

    await ws_manager.register(dep_uuid, websocket)

    try:
        await ws_manager.send_history(dep_uuid, websocket)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await ws_manager.unregister(dep_uuid, websocket)
