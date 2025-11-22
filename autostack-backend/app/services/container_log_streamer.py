"""Background task to stream container logs to deployment logs in real-time."""
import asyncio
import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import AsyncSessionLocal
from ..models import Deployment, DeploymentContainer, DeploymentLog
from .container_runtime import get_container_logs, is_docker_available


_log_streamer_task: asyncio.Task | None = None
_last_log_fetch: dict[uuid.UUID, datetime] = {}


async def stream_container_logs_task() -> None:
    """Background task that periodically fetches container logs for running deployments."""
    if not is_docker_available():
        return
    
    while True:
        try:
            await asyncio.sleep(10)  # Check every 10 seconds
            
            async with AsyncSessionLocal() as session:
                # Find all running deployments with containers
                result = await session.execute(
                    select(Deployment, DeploymentContainer)
                    .join(DeploymentContainer, Deployment.id == DeploymentContainer.deployment_id)
                    .where(
                        Deployment.status == "success",
                        DeploymentContainer.status == "running",
                    )
                )
                rows = result.all()
                
                for deployment, container in rows:
                    # Skip if we fetched logs recently (within last 30 seconds)
                    last_fetch = _last_log_fetch.get(deployment.id)
                    if last_fetch and (datetime.utcnow() - last_fetch).total_seconds() < 30:
                        continue
                    
                    try:
                        # Fetch recent logs (last 20 lines)
                        logs = await get_container_logs(session, deployment, container, tail=20)
                        
                        # Only append if there are new logs
                        if logs:
                            # Check if these logs are already in the database
                            existing_logs_result = await session.execute(
                                select(DeploymentLog)
                                .where(DeploymentLog.deployment_id == deployment.id)
                                .order_by(DeploymentLog.timestamp.desc())
                                .limit(20)
                            )
                            existing_log_messages = {log.message for log in existing_logs_result.scalars().all()}
                            
                            # Add only new logs
                            new_logs = [log for log in logs if f"[CONTAINER] {log}" not in existing_log_messages]
                            if new_logs:
                                for log_line in new_logs:
                                    log_entry = DeploymentLog(
                                        deployment_id=deployment.id,
                                        message=f"[CONTAINER] {log_line}",
                                        log_level="info",
                                        timestamp=datetime.utcnow(),
                                    )
                                    session.add(log_entry)
                                await session.commit()
                        
                        _last_log_fetch[deployment.id] = datetime.utcnow()
                    
                    except Exception:
                        # Silently ignore errors for individual containers
                        pass
        
        except Exception:
            # Continue running even if there's an error
            await asyncio.sleep(10)


def start_log_streamer() -> None:
    """Start the background log streaming task."""
    global _log_streamer_task
    if _log_streamer_task is None or _log_streamer_task.done():
        _log_streamer_task = asyncio.create_task(stream_container_logs_task())


def stop_log_streamer() -> None:
    """Stop the background log streaming task."""
    global _log_streamer_task
    if _log_streamer_task and not _log_streamer_task.done():
        _log_streamer_task.cancel()
        _log_streamer_task = None
