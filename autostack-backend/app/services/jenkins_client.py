from __future__ import annotations

import uuid

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..config import settings
from ..db import AsyncSessionLocal
from ..models import DeploymentLog, Deployment, Project


async def _log(deployment_id: uuid.UUID, message: str, level: str = "info") -> None:
    async with AsyncSessionLocal() as session:
        log = DeploymentLog(deployment_id=deployment_id, message=message, log_level=level)
        session.add(log)
        await session.commit()


async def trigger_jenkins_build(deployment: Deployment, project: Project | None) -> None:
    if not settings.jenkins_enable:
        return
    if not settings.jenkins_url:
        return
    if not settings.jenkins_user or not settings.jenkins_api_token:
        return

    deployment_id = deployment.id
    repo = project.repository if project is not None else None
    branch = deployment.branch or (project.branch if project is not None else None)

    params: dict[str, str] = {
        "DEPLOYMENT_ID": str(deployment_id),
    }
    if repo:
        params["REPOSITORY"] = repo
    if branch:
        params["BRANCH"] = branch

    job_name: str | None = None
    if project is not None and getattr(project, "jenkins_job_name", None):
        job_name = project.jenkins_job_name  # type: ignore[attr-defined]
    else:
        job_name = settings.jenkins_job_name

    if not job_name:
        return

    job_url = f"{str(settings.jenkins_url).rstrip('/')}/job/{job_name}/buildWithParameters"

    await _log(deployment_id, f"Triggering Jenkins job at {job_url} with params {params}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                job_url,
                params=params,
                auth=(settings.jenkins_user, settings.jenkins_api_token),
                timeout=10,
            )
        if response.status_code not in (200, 201, 202):
            await _log(
                deployment_id,
                f"Jenkins job trigger failed with status {response.status_code}: {response.text}",
                level="error",
            )
            return
        await _log(deployment_id, "Jenkins job triggered successfully")
    except Exception as exc:  # pragma: no cover - network errors
        await _log(deployment_id, f"Jenkins integration error: {exc}", level="error")
