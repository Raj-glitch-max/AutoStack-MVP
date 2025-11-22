from __future__ import annotations

import asyncio
import shutil
import socket
from asyncio.subprocess import PIPE
from datetime import datetime
from pathlib import Path
from typing import Iterable, Tuple

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..errors import ApiError
from ..models import (
    Deployment,
    DeploymentContainer,
    DeploymentHealthCheck,
    DeploymentRuntimeLog,
)


DOCKER_IMAGE = "nginx:alpine"


def is_docker_available() -> bool:
    if not settings.docker_enable:
        return False
    return shutil.which("docker") is not None


def find_free_port(start: int, end: int) -> int:
    for port in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError(f"No free port found in range {start}-{end}")


async def _run_docker(args: Iterable[str], timeout: int = 60) -> Tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec("docker", *args, stdout=PIPE, stderr=PIPE)
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise
    return proc.returncode, stdout.decode(errors="ignore"), stderr.decode(errors="ignore")


async def start_container(
    session: AsyncSession,
    deployment: Deployment,
    artifacts_dir: Path,
) -> DeploymentContainer:
    if not is_docker_available():
        raise ApiError("RUNTIME_UNAVAILABLE", "Docker runtime is disabled or not installed", 400)

    port = find_free_port(settings.runtime_port_range_start, settings.runtime_port_range_end)
    name = f"autostack-{deployment.id}"

    cmd = [
        "run",
        "-d",
        "--name",
        name,
        "-p",
        f"{port}:80",
        "-v",
        f"{str(artifacts_dir)}:/usr/share/nginx/html:ro",
        DOCKER_IMAGE,
    ]

    code, out, err = await _run_docker(cmd, timeout=settings.container_start_timeout)
    if code != 0 or not out.strip():
        message = (err or out or "unknown docker error").strip().splitlines()[0][:500]
        raise ApiError("RUNTIME_ERROR", f"Failed to start Docker container: {message}", 500)

    container_id = out.strip().splitlines()[0]

    container = DeploymentContainer(
        deployment_id=deployment.id,
        container_id=container_id,
        image=DOCKER_IMAGE,
        host="localhost",
        port=port,
        status="starting",
    )
    session.add(container)
    await session.flush()

    return container


async def start_dockerfile_runtime(
    session: AsyncSession,
    deployment: Deployment,
    repo_dir: Path,
    *,
    lambda_mode: bool = False,
) -> DeploymentContainer:
    """Build and run a Docker image from a user-provided Dockerfile in the repo.

    This is used when a project is configured with runtime="docker" and a Dockerfile
    is detected at the repository root. It mirrors the behaviour of start_container
    but uses the user's Dockerfile instead of a fixed nginx image.
    """

    if not is_docker_available():
        raise ApiError("RUNTIME_UNAVAILABLE", "Docker runtime is disabled or not installed", 400)

    port = find_free_port(settings.runtime_port_range_start, settings.runtime_port_range_end)
    name = f"autostack-{deployment.id}"
    image = f"autostack-{deployment.id}".lower()

    # Build image from the repository Dockerfile
    build_args = [
        "build",
        "-t",
        image,
        str(repo_dir),
    ]
    code, out, err = await _run_docker(build_args, timeout=settings.container_start_timeout)
    if code != 0:
        message = (err or out or "docker build failed").strip()
        raise ApiError("RUNTIME_ERROR", f"Failed to build Docker image from Dockerfile: {message}", 500)

    # Run container from the built image. Lambda-style base images expose
    # their runtime interface on port 8080 by default, while typical web
    # containers listen on port 80. lambda_mode controls which mapping we use.
    internal_port = 8080 if lambda_mode else 80
    run_args = [
        "run",
        "-d",
        "--name",
        name,
        "-p",
        f"{port}:{internal_port}",
        image,
    ]

    code, out, err = await _run_docker(run_args, timeout=settings.container_start_timeout)
    if code != 0 or not out.strip():
        message = (err or out or "unknown docker error").strip()
        raise ApiError("RUNTIME_ERROR", f"Failed to start Dockerfile container: {message}", 500)

    container_id = out.strip().splitlines()[0]

    container = DeploymentContainer(
        deployment_id=deployment.id,
        container_id=container_id,
        image=image,
        host="localhost",
        port=port,
        status="starting",
    )
    session.add(container)
    await session.flush()

    # For generic web containers, perform an HTTP health check on the root
    # URL. For Lambda-style images, we cannot rely on an HTTP 2xx status at
    # "/", so we skip the check and treat a successful docker run as
    # "running".
    if lambda_mode:
        container.status = "running"
        await session.flush()
        return container

    url = f"http://{container.host}:{container.port}/"
    hc = await record_health_check(session, deployment, url)
    container.status = "running" if hc.is_live else "failed"
    await session.flush()

    return container


async def stop_container(session: AsyncSession, container: DeploymentContainer) -> None:
    if not is_docker_available():
        container.status = "stopped"
        container.stopped_at = datetime.utcnow()
        await session.flush()
        return

    code, _out, _err = await _run_docker(["rm", "-f", container.container_id], timeout=30)
    now = datetime.utcnow()
    container.stopped_at = now
    container.status = "stopped" if code == 0 else "failed"
    await session.flush()


async def get_container_logs(
    session: AsyncSession,
    deployment: Deployment,
    container: DeploymentContainer,
    tail: int = 200,
) -> list[str]:
    if not is_docker_available():
        raise ApiError("RUNTIME_UNAVAILABLE", "Docker runtime is disabled or not installed", 400)

    code, out, err = await _run_docker(["logs", f"--tail={tail}", container.container_id], timeout=30)
    if code != 0:
        message = (err or out or "failed to read docker logs").strip().splitlines()[0][:500]
        raise ApiError("RUNTIME_ERROR", f"Failed to read Docker logs: {message}", 500)

    lines = [line for line in out.splitlines() if line]
    now = datetime.utcnow()
    for line in lines:
        session.add(
            DeploymentRuntimeLog(
                deployment_id=deployment.id,
                source="docker",
                log_level=None,
                message=line[:2000],
                timestamp=now,
            )
        )
    await session.flush()
    return lines


async def latest_container(session: AsyncSession, deployment_id) -> DeploymentContainer | None:
    result = await session.execute(
        select(DeploymentContainer)
        .where(DeploymentContainer.deployment_id == deployment_id)
        .order_by(DeploymentContainer.created_at.desc())
    )
    return result.scalar_one_or_none()


async def record_health_check(
    session: AsyncSession,
    deployment: Deployment,
    url: str,
) -> DeploymentHealthCheck:
    status: int | None = None
    latency_ms: int | None = None
    ok = False

    try:
        async with httpx.AsyncClient() as client:
            start = asyncio.get_event_loop().time()
            resp = await client.get(url, timeout=settings.container_start_timeout)
            end = asyncio.get_event_loop().time()
        status = resp.status_code
        latency_ms = int((end - start) * 1000)
        ok = 200 <= resp.status_code < 400
    except Exception:
        ok = False

    hc = DeploymentHealthCheck(
        deployment_id=deployment.id,
        url=url,
        http_status=status,
        latency_ms=latency_ms,
        is_live=ok,
        checked_at=datetime.utcnow(),
    )
    session.add(hc)
    await session.flush()
    return hc
