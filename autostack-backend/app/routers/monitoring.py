"""Monitoring API endpoints.

Provides real system metrics and monitoring data, including pipeline metrics.
"""

import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..build_engine import JenkinsStylePipeline
from ..db import get_db
from ..errors import ApiError
from ..models import Deployment, DeploymentStage
from ..security import get_current_user
from ..services.real_k8s_orchestrator import get_cluster_snapshot
from ..services.monitoring import monitoring_service

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


@router.get("/metrics")
async def get_metrics_summary(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive monitoring metrics"""
    metrics = await monitoring_service.get_metrics_summary()
    return metrics


@router.get("/system")
async def get_system_metrics(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get system metrics only"""
    metrics = await monitoring_service.collect_system_metrics()
    return metrics


@router.get("/docker")
async def get_docker_metrics(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get Docker container metrics"""
    metrics = await monitoring_service.collect_docker_metrics()
    return metrics


@router.get("/deployments")
async def get_deployment_metrics(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get deployment and pod metrics"""
    metrics = await monitoring_service.collect_deployment_metrics()
    return metrics


@router.get("/application")
async def get_application_metrics(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get application-specific metrics"""
    metrics = await monitoring_service.collect_application_metrics()
    return metrics


@router.get("/cluster")
async def get_cluster_status(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get real Kubernetes cluster status via kubectl JSON output"""
    snapshot = get_cluster_snapshot(None)
    pods_raw = snapshot.get("pods", [])
    services_raw = snapshot.get("services", [])
    deployments_raw = snapshot.get("deployments", [])

    total_pods = len(pods_raw)
    running_pods = sum(
        1 for pod in pods_raw if pod.get("status", {}).get("phase") == "Running"
    )

    cluster_status = {
        "total_pods": total_pods,
        "running_pods": running_pods,
        "services": len(services_raw),
        "deployments": len(deployments_raw),
        "docker_available": True,
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Detailed pod information for the UI
    pods_info = []
    for pod in pods_raw:
        meta = pod.get("metadata", {})
        status = pod.get("status", {})
        labels = meta.get("labels", {}) or {}
        container_statuses = status.get("containerStatuses", []) or []
        ready = bool(container_statuses) and all(cs.get("ready") for cs in container_statuses)
        container_id = (
            container_statuses[0].get("containerID") if container_statuses else None
        )

        pods_info.append(
            {
                "id": meta.get("uid") or meta.get("name"),
                "name": meta.get("name"),
                "status": status.get("phase"),
                "ready": ready,
                "created_at": meta.get("creationTimestamp"),
                "container_id": container_id,
                "metrics": {},
                "health": {
                    "healthy": ready and status.get("phase") == "Running",
                    "reason": None,
                    "status": status.get("phase"),
                    "last_check": datetime.utcnow().isoformat(),
                },
                "labels": labels,
            }
        )

    # Service information for the UI
    services_info = []
    for svc in services_raw:
        meta = svc.get("metadata", {})
        spec = svc.get("spec", {})
        services_info.append(
            {
                "id": meta.get("uid") or meta.get("name"),
                "name": meta.get("name"),
                "selector": spec.get("selector") or {},
                "ports": [p.get("port") for p in spec.get("ports", [])],
                "endpoints": [],
                "created_at": meta.get("creationTimestamp"),
            }
        )

    # Map deployments by name for the frontend summary
    deployments_map: dict[str, dict] = {}
    for dep in deployments_raw:
        meta = dep.get("metadata", {})
        spec = dep.get("spec", {})
        status = dep.get("status", {})
        name = meta.get("name")
        if not name:
            continue
        deployments_map[name] = {
            "name": name,
            "namespace": meta.get("namespace"),
            "replicas": spec.get("replicas"),
            "available_replicas": status.get("availableReplicas", 0),
            "labels": meta.get("labels") or {},
        }

    return {
        "cluster": cluster_status,
        "pods": pods_info,
        "services": services_info,
        "deployments": deployments_map,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/history/{metric_type}")
async def get_metrics_history(
    metric_type: str,
    hours: int = 24,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get historical metrics for a specific type"""
    history = await monitoring_service.get_metrics_history(metric_type, hours)
    return {
        "metric_type": metric_type,
        "hours": hours,
        "data": history,
        "count": len(history)
    }


@router.get("/alerts")
async def get_alerts(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current alerts"""
    return {
        "alerts": monitoring_service.alerts[-20:],  # Last 20 alerts
        "count": len(monitoring_service.alerts)
    }


@router.websocket("/live")
async def websocket_monitoring(websocket: WebSocket):
    """WebSocket for real-time monitoring updates"""
    await websocket.accept()
    
    try:
        # Send initial metrics
        initial_metrics = await monitoring_service.get_metrics_summary()
        await websocket.send_text(json.dumps({
            "type": "metrics_update",
            "data": initial_metrics
        }))
        
        # Send updates every 10 seconds
        import asyncio
        while True:
            await asyncio.sleep(10)
            
            try:
                metrics = await monitoring_service.get_metrics_summary()
                await websocket.send_text(json.dumps({
                    "type": "metrics_update",
                    "data": metrics,
                    "timestamp": datetime.utcnow().isoformat()
                }))
            except Exception as e:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": str(e)
                }))
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": str(e)
            }))
        except:
            pass


@router.get("/pipeline/{deployment_id}")
async def get_pipeline_metrics(
    deployment_id: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get Jenkins-style pipeline metrics for a real deployment.

    Uses recorded DeploymentStage rows to compute per-stage timings and
    JenkinsStylePipeline.STAGES for overall estimated duration.
    """

    try:
        dep_uuid = uuid.UUID(deployment_id)
    except ValueError:
        raise ApiError("NOT_FOUND", "Deployment not found", 404)

    result = await db.execute(select(Deployment).where(Deployment.id == dep_uuid))
    deployment = result.scalar_one_or_none()
    if not deployment or deployment.is_deleted or deployment.user_id != current_user.id:
        raise ApiError("NOT_FOUND", "Deployment not found", 404)

    stages_result = await db.execute(
        select(DeploymentStage)
        .where(DeploymentStage.deployment_id == dep_uuid)
        .order_by(DeploymentStage.created_at.asc())
    )
    stages = list(stages_result.scalars().all())

    stage_items: list[dict] = []
    total_duration = 0.0

    for stage in stages:
        start = stage.started_at or stage.created_at
        end = stage.completed_at or datetime.utcnow()
        duration = max((end - start).total_seconds(), 0.0)
        total_duration += duration

        stage_items.append(
            {
                "name": stage.stage_name.upper().replace(" ", "_"),
                "display_name": stage.stage_name,
                "status": stage.status.upper(),
                "duration_seconds": duration,
                "start_time": start.isoformat() + "Z",
                "end_time": stage.completed_at.isoformat() + "Z" if stage.completed_at else None,
            }
        )

    # Use JenkinsStylePipeline stage metadata for an overall estimate
    estimated_total = sum(info.get("estimated_time", 0) for info in JenkinsStylePipeline.STAGES.values())
    efficiency = (estimated_total / total_duration * 100.0) if total_duration > 0 else None

    pipeline_start = stage_items[0]["start_time"] if stage_items else None
    pipeline_end = stage_items[-1]["end_time"] if stage_items else None

    return {
        "deployment_id": deployment_id,
        "pipeline": {
            "style": "jenkins",
            "stages": stage_items,
            "total_duration": total_duration,
            "estimated_duration": estimated_total,
            "efficiency": efficiency,
            "start_time": pipeline_start,
            "end_time": pipeline_end,
        },
        "timestamp": datetime.utcnow().isoformat(),
    }
