from __future__ import annotations

import asyncio
import os
import platform
import shlex
import shutil
import subprocess
import uuid
from asyncio.subprocess import PIPE
from contextlib import suppress
from datetime import datetime
from pathlib import Path
import time
import json

import psutil
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .db import AsyncSessionLocal
from .errors import ApiError
from .models import Deployment, DeploymentLog, Project
from .services.container_runtime import is_docker_available, record_health_check, start_container, start_dockerfile_runtime
from .services.docker_builder import build_static_site_image
from .services.real_k8s_orchestrator import K8sDeploymentConfig, deploy_static_app
from .services.jenkins_client import trigger_jenkins_build
from .services.stages import STAGE_LABELS, StageKey, set_stage_status
from .websockets import broadcast_deployment_event, ws_manager


# Jenkins-style pipeline stages with real timing
class JenkinsStylePipeline:
    """Simulates Jenkins pipeline with real stages and timing"""
    
    STAGES = {
        "SCM_CHECKOUT": {
            "name": "Source Code Management",
            "description": "Cloning repository from GitHub",
            "estimated_time": 30,  # seconds
            "color": "#E3F2FD"
        },
        "BUILD_SETUP": {
            "name": "Build Environment Setup", 
            "description": "Setting up build tools and dependencies",
            "estimated_time": 15,
            "color": "#F3E5F5"
        },
        "COMPILE": {
            "name": "Compile & Build",
            "description": "Compiling source code and building artifacts",
            "estimated_time": 120,
            "color": "#E8F5E8"
        },
        "TEST": {
            "name": "Test Execution",
            "description": "Running test suites",
            "estimated_time": 45,
            "color": "#FFF3E0"
        },
        "PACKAGE": {
            "name": "Package Artifacts",
            "description": "Packaging application for deployment",
            "estimated_time": 20,
            "color": "#FCE4EC"
        },
        "DEPLOY": {
            "name": "Deploy Application",
            "description": "Deploying to production environment",
            "estimated_time": 35,
            "color": "#E0F2F1"
        },
        "VERIFY": {
            "name": "Post-Deployment Verification",
            "description": "Health checks and verification",
            "estimated_time": 10,
            "color": "#E1F5FE"
        }
    }
    
    def __init__(self, deployment_id: uuid.UUID):
        self.deployment_id = deployment_id
        self.stage_timings = {}
        self.pipeline_start_time = None
        
    async def execute_stage(self, stage_key: str, stage_function, *args, **kwargs):
        """Execute a pipeline stage with timing and logging"""
        stage_info = self.STAGES.get(stage_key, {})
        stage_start = time.time()
        
        # Log stage start
        await self._log_stage_start(stage_key, stage_info)
        
        try:
            # Execute the actual stage function
            result = await stage_function(*args, **kwargs)
            
            # Calculate timing
            stage_duration = time.time() - stage_start
            self.stage_timings[stage_key] = {
                "duration": stage_duration,
                "estimated": stage_info.get("estimated_time", 0),
                "status": "SUCCESS"
            }
            
            # Log stage completion
            await self._log_stage_complete(stage_key, stage_duration, stage_info)
            
            return result
            
        except Exception as e:
            # Log stage failure
            stage_duration = time.time() - stage_start
            self.stage_timings[stage_key] = {
                "duration": stage_duration,
                "estimated": stage_info.get("estimated_time", 0),
                "status": "FAILED",
                "error": str(e)
            }
            
            await self._log_stage_failed(stage_key, str(e), stage_info)
            raise
    
    async def _log_stage_start(self, stage_key: str, stage_info: dict):
        """Log stage start with Jenkins-style formatting"""
        await broadcast_deployment_event(
            self.deployment_id,
            {
                "type": "pipeline_stage",
                "stage": stage_key,
                "status": "STARTED",
                "message": f"[{stage_key}] Starting: {stage_info.get('description', '')}",
                "timestamp": datetime.utcnow().isoformat(),
                "pipeline_style": "jenkins",
            },
        )
    
    async def _log_stage_complete(self, stage_key: str, duration: float, stage_info: dict):
        """Log stage completion with timing"""
        await broadcast_deployment_event(
            self.deployment_id,
            {
                "type": "pipeline_stage",
                "stage": stage_key,
                "status": "SUCCESS",
                "message": f"[{stage_key}] Completed in {duration:.2f}s (estimated: {stage_info.get('estimated_time', 0)}s)",
                "timestamp": datetime.utcnow().isoformat(),
                "duration": duration,
                "pipeline_style": "jenkins",
            },
        )
    
    async def _log_stage_failed(self, stage_key: str, error: str, stage_info: dict):
        """Log stage failure"""
        await broadcast_deployment_event(
            self.deployment_id,
            {
                "type": "pipeline_stage",
                "stage": stage_key,
                "status": "FAILED",
                "message": f"[{stage_key}] FAILED: {error}",
                "timestamp": datetime.utcnow().isoformat(),
                "error": error,
                "pipeline_style": "jenkins",
            },
        )
    
    def get_pipeline_summary(self) -> dict:
        """Get complete pipeline summary with timings"""
        total_duration = sum(timing["duration"] for timing in self.stage_timings.values())
        total_estimated = sum(self.STAGES[stage]["estimated_time"] for stage in self.STAGES)
        
        return {
            "pipeline_id": str(self.deployment_id),
            "total_duration": total_duration,
            "total_estimated": total_estimated,
            "stages": self.stage_timings,
            "efficiency": (total_estimated / total_duration * 100) if total_duration > 0 else 0,
            "pipeline_style": "jenkins"
        }


_cancel_flags: dict[uuid.UUID, asyncio.Event] = {}
DEFAULT_OUTPUT_DIRS = ["dist", "build", "out", "public", "site"]


def _parse_env_block(raw: str | None) -> dict[str, str]:
    env: dict[str, str] = {}
    if not raw:
        return env
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()
    return env


def get_cancel_flag(deployment_id: uuid.UUID) -> asyncio.Event:
    flag = _cancel_flags.get(deployment_id)
    if not flag:
        flag = asyncio.Event()
        _cancel_flags[deployment_id] = flag
    return flag


async def cancel_deployment_run(deployment_id: uuid.UUID) -> None:
    flag = get_cancel_flag(deployment_id)
    flag.set()


def _clear_cancel_flag(deployment_id: uuid.UUID) -> None:
    _cancel_flags.pop(deployment_id, None)


def _kill_process_tree(pid: int | None) -> None:
    if pid is None:
        return
    try:
        parent = psutil.Process(pid)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        if platform.system().lower().startswith("win"):
            with suppress(subprocess.SubprocessError):
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True, check=False)
        return

    children = parent.children(recursive=True)
    for child in children:
        with suppress(psutil.Error):
            child.kill()
    with suppress(psutil.Error):
        parent.kill()


def _resolve_output_directory(
    repo_dir: Path,
    configured: str | None,
    *,
    allow_repo_root: bool = False,
) -> tuple[Path, str]:
    candidates: list[str] = []
    if configured:
        candidates.append(configured.strip("/\\"))
    for default in DEFAULT_OUTPUT_DIRS:
        if default not in candidates:
            candidates.append(default)

    for candidate in candidates:
        if not candidate:
            continue
        candidate_path = repo_dir / candidate
        if candidate_path.exists() and candidate_path.is_dir():
            return candidate_path, candidate
    if allow_repo_root:
        return repo_dir, "."
    raise FileNotFoundError(f"Output directory not found (tried: {', '.join(candidates)})")


async def _capture_stdout(cmd: str, cwd: Path) -> tuple[int, str]:
    process = await asyncio.create_subprocess_shell(cmd, cwd=str(cwd), stdout=PIPE, stderr=PIPE)
    stdout, _ = await process.communicate()
    return process.returncode, stdout.decode(errors="ignore").strip()


async def _collect_commit_metadata(repo_dir: Path) -> dict[str, str | None]:
    commands = {
        "commit_hash": "git rev-parse HEAD",
        "commit_message": "git log -1 --pretty=%B",
        "author": "git log -1 --pretty=%an",
        "timestamp": "git log -1 --pretty=%at",
    }
    metadata: dict[str, str | None] = {}
    for key, cmd in commands.items():
        code, output = await _capture_stdout(cmd, repo_dir)
        metadata[key] = output if code == 0 else None
    return metadata


async def _record_failure(
    session: AsyncSession,
    deployment: Deployment,
    stage_key: StageKey,
    reason: str,
    log_message: str,
) -> None:
    deployment.failed_reason = reason
    await _append_log(session, deployment.id, log_message, "error")
    await set_stage_status(session, deployment.id, stage_key, "failed")


async def _record_cancelled(
    session: AsyncSession,
    deployment: Deployment,
    stage_key: StageKey,
    reason: str,
) -> None:
    deployment.status = "cancelled"
    deployment.failed_reason = reason
    await _append_log(session, deployment.id, "Deployment cancelled by user", "error")
    await set_stage_status(session, deployment.id, stage_key, "cancelled")


async def _append_log(session: AsyncSession | None, deployment_id: uuid.UUID, message: str, level: str = "info") -> None:
    if session:
        log = DeploymentLog(deployment_id=deployment_id, message=message, log_level=level)
        session.add(log)
        await session.commit()
    else:
        async with AsyncSessionLocal() as log_session:
            log = DeploymentLog(deployment_id=deployment_id, message=message, log_level=level)
            log_session.add(log)
            await log_session.commit()
    await ws_manager.broadcast_log(deployment_id, message)


async def _update_status(
    session: AsyncSession,
    deployment: Deployment,
    status: str,
    stage_key: StageKey | None = None,
) -> None:
    deployment.status = status
    stage_name = STAGE_LABELS.get(stage_key) if stage_key else None
    if stage_key:
        await set_stage_status(session, deployment.id, stage_key, "in_progress")
    await session.flush()
    await broadcast_deployment_event(
        deployment.id,
        {
            "type": "status_update",
            "status": status,
            "stage": stage_name or status.title(),
        },
    )


async def _finalize_deployment(session: AsyncSession, deployment: Deployment, success: bool) -> None:
    deployment.completed_at = datetime.utcnow()
    if deployment.started_at and deployment.completed_at:
        deployment.build_duration_seconds = int((deployment.completed_at - deployment.started_at).total_seconds())
    if success:
        deployment.status = "success"
        await set_stage_status(session, deployment.id, "success", "completed")
    else:
        if deployment.status != "cancelled":
            deployment.status = "failed"
            await set_stage_status(session, deployment.id, "failed", "failed")
        else:
            await set_stage_status(session, deployment.id, "cancelled", "completed")
    await session.flush()
    await broadcast_deployment_event(
        deployment.id,
        {
            "type": "deployment_complete",
            "status": deployment.status,
            "duration": f"{deployment.build_duration_seconds or 0}s",
            "url": deployment.deployed_url,
        },
    )


async def _run_command(
    deployment_id: uuid.UUID,
    session: AsyncSession,
    cmd: str,
    cwd: Path,
    cancel_flag: asyncio.Event,
    env: dict[str, str] | None = None,
) -> int:
    await _append_log(session, deployment_id, f"$ {cmd}")
    process = await asyncio.create_subprocess_shell(cmd, cwd=str(cwd), stdout=PIPE, stderr=PIPE, env=env)

    log_queue: asyncio.Queue[tuple[str, str] | None] = asyncio.Queue()

    async def _stream(pipe, level: str) -> None:
        assert pipe is not None
        while True:
            if cancel_flag.is_set():
                _kill_process_tree(process.pid)
                break
            line = await pipe.readline()
            if not line:
                break
            text = line.decode(errors="ignore").rstrip()
            if text:
                await log_queue.put((level, text))

    async def _drain_logs() -> None:
        while True:
            item = await log_queue.get()
            if item is None:
                break
            level, text = item
            await _append_log(session, deployment_id, text, level)

    writer = asyncio.create_task(_drain_logs())
    await asyncio.gather(_stream(process.stdout, "info"), _stream(process.stderr, "error"))
    await log_queue.put(None)
    await writer
    if cancel_flag.is_set():
        _kill_process_tree(process.pid)
    return await process.wait()


async def run_deployment_job(deployment_id: uuid.UUID) -> None:
    cancel_flag = get_cancel_flag(deployment_id)
    repo_dir = Path(".autostack_builds") / str(deployment_id)
    artifacts_root = Path(settings.autostack_deploy_dir)
    artifacts_dir = artifacts_root / str(deployment_id)

    os.makedirs(repo_dir, exist_ok=True)
    os.makedirs(artifacts_root, exist_ok=True)

    async with AsyncSessionLocal() as session:
        pipeline: JenkinsStylePipeline | None = None
        result = await session.execute(
            select(Deployment).options().where(Deployment.id == deployment_id)
        )
        deployment = result.scalar_one_or_none()
        if not deployment:
            return

        project = await session.get(Project, deployment.project_id)
        if not project:
            return

        deployment.started_at = datetime.utcnow()
        await set_stage_status(session, deployment.id, "queued", "completed")
        pipeline = JenkinsStylePipeline(deployment.id)
        pipeline.pipeline_start_time = time.time()
        await pipeline._log_stage_start("SCM_CHECKOUT", JenkinsStylePipeline.STAGES.get("SCM_CHECKOUT", {}))
        await session.commit()

        # Ensure required tools are available before starting clone/install/build
        missing_reasons: list[str] = []
        if shutil.which("git") is None:
            missing_reasons.append("GIT NOT INSTALLED")
        if shutil.which("node") is None:
            missing_reasons.append("NODE NOT INSTALLED")
        if not any(shutil.which(t) is not None for t in ("npm", "yarn", "pnpm")):
            missing_reasons.append("NPM/YARN/PNPM NOT INSTALLED")

        if missing_reasons:
            reason = "; ".join(missing_reasons)
            await _record_failure(session, deployment, "queued", reason, reason)
            await session.commit()
            await _finalize_deployment(session, deployment, success=False)
            await session.commit()
            return

        env_block = _parse_env_block(project.env_vars)
        if deployment.env_vars:
            env_block.update(_parse_env_block(deployment.env_vars))

        repo_identifier = project.repository
        if repo_identifier.startswith(("http://", "https://")) or repo_identifier.endswith(".git"):
            clone_url = repo_identifier
        else:
            clone_url = f"https://github.com/{repo_identifier}.git"
        try:
            repo_identifier = project.repository
            if repo_identifier.startswith(("http://", "https://")) or repo_identifier.endswith(".git"):
                clone_url = repo_identifier
            else:
                clone_url = f"https://github.com/{repo_identifier}.git"

            runtime_env = os.environ.copy()
            runtime_env.update(env_block)
            runtime_env["AUTOSTACK_DEPLOYMENT_ID"] = str(deployment.id)
            runtime_env["AUTOSTACK_REPOSITORY"] = repo_identifier
            if deployment.branch:
                runtime_env["AUTOSTACK_BRANCH"] = deployment.branch

            await _update_status(session, deployment, "cloning", "cloning")
            await session.commit()
            try:
                clone_exit = await asyncio.wait_for(
                    _run_command(
                        deployment_id,
                        session,
                        f"git clone {shlex.quote(clone_url)} .",
                        repo_dir,
                        cancel_flag,
                        env=runtime_env.copy(),
                    ),
                    timeout=settings.build_timeout_seconds,
                )
            except asyncio.TimeoutError:
                reason = f"Build timed out during {STAGE_LABELS['cloning']}"
                await _record_failure(session, deployment, "cloning", reason, reason)
                cancel_flag.set()
                await session.commit()
                await _finalize_deployment(session, deployment, success=False)
                await session.commit()
                return
            await session.commit()
            if cancel_flag.is_set():
                await _record_cancelled(session, deployment, "cloning", "Cancelled by user during clone")
                await session.commit()
                await _finalize_deployment(session, deployment, success=False)
                await session.commit()
                return
            if clone_exit != 0:
                await _record_failure(session, deployment, "cloning", "Repository clone failed", "Repository clone failed")
                await session.commit()
                await _finalize_deployment(session, deployment, success=False)
                await session.commit()
                return
            await set_stage_status(session, deployment.id, "cloning", "completed")

            branch_name = (deployment.branch or project.branch or "main").strip()
            await _append_log(session, deployment_id, f"Checking out branch: {branch_name}")
            await _update_status(session, deployment, "checkout", "checkout")
            await session.commit()
            checkout_exit = await _run_command(
                deployment_id,
                session,
                f"git checkout {shlex.quote(branch_name)}",
                repo_dir,
                cancel_flag,
                env=runtime_env.copy(),
            )
            await session.commit()
            if cancel_flag.is_set():
                await _record_cancelled(session, deployment, "checkout", "Cancelled by user during checkout")
                await session.commit()
                await _finalize_deployment(session, deployment, success=False)
                await session.commit()
                return
            if checkout_exit != 0:
                await _record_failure(
                    session,
                    deployment,
                    "checkout",
                    f"Git checkout failed for branch {branch_name}",
                    "Branch checkout failed",
                )
                await session.commit()
                await _finalize_deployment(session, deployment, success=False)
                await session.commit()
                return
            await set_stage_status(session, deployment.id, "checkout", "completed")

            metadata = await _collect_commit_metadata(repo_dir)
            if metadata.get("commit_hash"):
                deployment.commit_hash = metadata["commit_hash"]
                deployment.commit_message = metadata.get("commit_message")
                deployment.author = metadata.get("author")
                timestamp = metadata.get("timestamp")
                if timestamp:
                    with suppress(ValueError):
                        deployment.commit_timestamp = datetime.utcfromtimestamp(int(timestamp))
            await session.flush()

            # Detect repo layout to decide whether to use Dockerfile runtime or the
            # Node/static build pipeline. This allows Dockerfile-only repos (for
            # example, Python or Lambda-style apps) to work without requiring the
            # user to manually toggle the runtime in the UI.
            dockerfile_path = repo_dir / "Dockerfile"
            dockerfile_exists = dockerfile_path.is_file()
            package_json_exists = (repo_dir / "package.json").is_file()
            project_runtime = (getattr(project, "runtime", "static") or "static").strip().lower()

            # Heuristically detect Lambda-style Docker base images so the
            # runtime can adjust port mappings and health checks.
            lambda_base_image = False
            if dockerfile_exists:
                try:
                    docker_text = dockerfile_path.read_text(encoding="utf-8", errors="ignore")
                    for line in docker_text.splitlines():
                        stripped = line.strip()
                        if stripped.upper().startswith("FROM "):
                            parts = stripped.split()
                            if len(parts) >= 2:
                                base_image = parts[1]
                                if "public.ecr.aws/lambda" in base_image or "aws-lambda" in base_image:
                                    lambda_base_image = True
                            break
                except Exception:
                    lambda_base_image = False

            # Use Dockerfile runtime when Docker is enabled and a Dockerfile exists.
            # Preference order:
            #   1) If project.runtime == "docker" -> always use Dockerfile
            #   2) If there is no package.json (non-Node app) but a Dockerfile exists,
            #      auto-switch to Dockerfile runtime so Python/Lambda apps work
            #      out-of-the-box.
            use_dockerfile_runtime = (
                settings.docker_enable
                and dockerfile_exists
                and (project_runtime == "docker" or not package_json_exists)
            )

            if dockerfile_exists and not settings.docker_enable:
                await _append_log(
                    session,
                    deployment_id,
                    "Dockerfile detected but Docker runtime is disabled on the server (DOCKER_ENABLE=false); falling back to static pipeline",
                    "warning",
                )

            if use_dockerfile_runtime:
                # Persist runtime preference so future deployments treat this as a
                # Docker project even if it was initially created as static.
                if project_runtime != "docker":
                    project.runtime = "docker"
                    await session.flush()

                await _append_log(
                    session,
                    deployment_id,
                    "Dockerfile detected and runtime set to 'docker'; using Dockerfile-based runtime and skipping Node build",
                )

                await _update_status(session, deployment, "building", "building")
                await session.commit()

                try:
                    container = await start_dockerfile_runtime(
                        session,
                        deployment,
                        repo_dir,
                        lambda_mode=lambda_base_image,
                    )
                    url = f"http://{container.host}:{container.port}/"
                    deployment.deployed_url = url
                    
                    # Add Lambda-specific instructions if this is a Lambda container
                    if lambda_base_image:
                        await _append_log(
                            session,
                            deployment_id,
                            f"Lambda container started at {url}",
                        )
                        await _append_log(
                            session,
                            deployment_id,
                            "NOTE: Lambda containers expose a Runtime API, not a web server.",
                        )
                        await _append_log(
                            session,
                            deployment_id,
                            f"To invoke your Lambda function, POST to: {url}2015-03-31/functions/function/invocations",
                        )
                    else:
                        await _append_log(
                            session,
                            deployment_id,
                            f"Dockerfile runtime container started at {url}",
                        )
                    
                    # Fetch initial container logs
                    try:
                        from .services.container_runtime import get_container_logs
                        await _append_log(session, deployment_id, "--- Container Logs ---")
                        logs = await get_container_logs(session, deployment, container, tail=50)
                        if logs:
                            for log_line in logs:
                                await _append_log(session, deployment_id, f"[CONTAINER] {log_line}")
                        else:
                            await _append_log(session, deployment_id, "[CONTAINER] No logs yet")
                    except Exception as log_exc:
                        await _append_log(session, deployment_id, f"Failed to fetch container logs: {log_exc}", "warning")
                    
                    await set_stage_status(session, deployment.id, "building", "completed")
                    await _finalize_deployment(session, deployment, success=True)
                    await session.commit()
                except ApiError as exc:
                    reason = f"Dockerfile runtime error: {exc.message}"
                    await _record_failure(session, deployment, "building", reason, reason)
                    await session.commit()
                    await _finalize_deployment(session, deployment, success=False)
                    await session.commit()
                except Exception as exc:  # pragma: no cover - runtime dependent
                    import traceback
                    tb = traceback.format_exc()
                    reason = f"Dockerfile runtime unexpected error: {type(exc).__name__}: {exc}"
                    await _record_failure(session, deployment, "building", reason, f"{reason}\n{tb}")
                    await session.commit()
                    await _finalize_deployment(session, deployment, success=False)
                    await session.commit()

                return

            if package_json_exists:
                await _update_status(session, deployment, "installing", "installing")
                await session.commit()

                if (repo_dir / "pnpm-lock.yaml").exists():
                    install_cmd = "pnpm install"
                elif (repo_dir / "yarn.lock").exists():
                    install_cmd = "yarn install"
                elif (repo_dir / "package-lock.json").exists():
                    install_cmd = "npm ci"
                else:
                    install_cmd = "npm install"

                await _append_log(session, deployment_id, f"Using package manager command: {install_cmd}")
                try:
                    exit_code = await asyncio.wait_for(
                        _run_command(
                            deployment_id, session, install_cmd, repo_dir, cancel_flag, env=runtime_env.copy()
                        ),
                        timeout=settings.build_timeout_seconds,
                    )
                except asyncio.TimeoutError:
                    reason = f"Build timed out during {STAGE_LABELS['installing']}"
                    await _record_failure(session, deployment, "installing", reason, reason)
                    cancel_flag.set()
                    await session.commit()
                    await _finalize_deployment(session, deployment, success=False)
                    await session.commit()
                    return
                await session.commit()
                if cancel_flag.is_set():
                    await _record_cancelled(session, deployment, "installing", "Cancelled by user during dependency installation")
                    await session.commit()
                    await _finalize_deployment(session, deployment, success=False)
                    await session.commit()
                    return
                if exit_code != 0:
                    await _record_failure(session, deployment, "installing", "Dependency installation failed", "Dependency installation failed")
                    await session.commit()
                    await _finalize_deployment(session, deployment, success=False)
                    await session.commit()
                    return
                await set_stage_status(session, deployment.id, "installing", "completed")

                await _update_status(session, deployment, "building", "building")
                await session.commit()

                build_cmd = project.build_command or "npm run build"
                await _append_log(session, deployment_id, f"Running build command: {build_cmd}")
                try:
                    exit_code = await asyncio.wait_for(
                        _run_command(
                            deployment_id, session, build_cmd, repo_dir, cancel_flag, env=runtime_env.copy()
                        ),
                        timeout=settings.build_timeout_seconds,
                    )
                except asyncio.TimeoutError:
                    reason = f"Build timed out during {STAGE_LABELS['building']}"
                    await _record_failure(session, deployment, "building", reason, reason)
                    cancel_flag.set()
                    await session.commit()
                    await _finalize_deployment(session, deployment, success=False)
                    await session.commit()
                    return
                await session.commit()
                if cancel_flag.is_set():
                    await _record_cancelled(session, deployment, "building", "Cancelled by user during build")
                    await session.commit()
                    await _finalize_deployment(session, deployment, success=False)
                    await session.commit()
                    return
                if exit_code != 0:
                    await _record_failure(session, deployment, "building", "Build failed (non-zero exit code)", "Build failed")
                    await session.commit()
                    await _finalize_deployment(session, deployment, success=False)
                    await session.commit()
                    return
                await set_stage_status(session, deployment.id, "building", "completed")
            else:
                await _append_log(
                    session,
                    deployment_id,
                    "package.json not found; skipping dependency installation and build, serving repository root",
                    "warning",
                )
                await set_stage_status(session, deployment.id, "installing", "completed")
                await set_stage_status(session, deployment.id, "building", "completed")

            await _update_status(session, deployment, "copying", "copying")
            await session.commit()

            try:
                output_dir, detected = _resolve_output_directory(
                    repo_dir,
                    project.output_dir,
                    allow_repo_root=not package_json_exists,
                )
            except FileNotFoundError as exc:
                await _record_failure(session, deployment, "copying", str(exc), str(exc))
                await session.commit()
                await _finalize_deployment(session, deployment, success=False)
                await session.commit()
                return

            if project.output_dir != detected:
                project.output_dir = detected

            # Atomic artifact copy using a temporary directory, ensuring index.html exists
            temp_dir = artifacts_root / f"{deployment.id}__tmp"
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            shutil.copytree(output_dir, temp_dir)

            index_path = temp_dir / "index.html"
            if not index_path.is_file():
                reason = "index.html missing"
                await _record_failure(session, deployment, "copying", reason, reason)
                shutil.rmtree(temp_dir, ignore_errors=True)
                await session.commit()
                await _finalize_deployment(session, deployment, success=False)
                await session.commit()
                return

            if artifacts_dir.exists():
                shutil.rmtree(artifacts_dir)
            os.replace(temp_dir, artifacts_dir)
            await set_stage_status(session, deployment.id, "copying", "completed")

            # Default to static artifact URL
            base = str(settings.backend_url).rstrip("/")
            artifact_url = f"{base}/artifacts/{deployment.id}/index.html"
            deployment.deployed_url = artifact_url

            built_image: str | None = None
            # Optionally start Docker runtime if enabled and project is configured for it
            runtime_url: str | None = None
            if settings.docker_enable and getattr(project, "runtime", "static") == "docker":
                if not is_docker_available():
                    await _append_log(
                        session,
                        deployment.id,
                        "Docker is not available on host; serving static artifacts only",
                        "warning",
                    )
                else:
                    try:
                        container = await start_container(session, deployment, artifacts_dir)
                        url = f"http://{container.host}:{container.port}/"
                        hc = await record_health_check(session, deployment, url)
                        container.status = "running" if hc.is_live else "failed"
                        if hc.is_live:
                            runtime_url = url
                            await _append_log(
                                session,
                                deployment.id,
                                f"Runtime container started at {runtime_url}",
                            )
                        else:
                            await _append_log(
                                session,
                                deployment.id,
                                "Runtime container failed health check; falling back to static artifacts",
                                "error",
                            )
                        await session.flush()
                    except ApiError as exc:  # pragma: no cover - runtime optional
                        await _append_log(
                            session,
                            deployment.id,
                            f"Docker runtime error: {exc.message}",
                            "error",
                        )
                    except Exception as exc:  # pragma: no cover - runtime optional
                        await _append_log(
                            session,
                            deployment.id,
                            f"Docker runtime unexpected error: {exc}",
                            "error",
                        )

            if runtime_url:
                deployment.deployed_url = runtime_url

            if (
                settings.kubernetes_enable
                and settings.docker_enable
                and getattr(project, "runtime", "static") == "docker"
            ):
                # Build Docker image for Kubernetes deployment (best effort)
                try:
                    built_image = build_static_site_image(artifacts_dir, deployment.id)
                    await _append_log(
                        session,
                        deployment.id,
                        f"Built deployment image {built_image} for Kubernetes rollout",
                    )
                except Exception as exc:
                    built_image = None
                    await _append_log(
                        session,
                        deployment.id,
                        f"Docker image build failed, falling back to nginx: {exc}",
                        "error",
                    )

                try:
                    labels = {
                        "deployment_id": str(deployment.id),
                        "project_id": str(project.id),
                        "environment": "production" if deployment.is_production else "preview",
                    }
                    kcfg = K8sDeploymentConfig(
                        name=f"{project.name.lower()}-{str(deployment.id)[:8]}",
                        image=built_image or "nginx:alpine",
                        port=80,
                        env=env_block,
                        labels=labels,
                    )
                    k8s_info = deploy_static_app(kcfg)
                    # Record basic identifiers in the deployment failed_reason for now (no dedicated fields yet)
                    meta_str = json.dumps(
                        {
                            "k8s_namespace": k8s_info["namespace"],
                            "k8s_deployment": k8s_info["deployment_name"],
                            "k8s_service": k8s_info["service_name"],
                            "k8s_node_port": k8s_info.get("node_port"),
                        }
                    )
                    if deployment.failed_reason:
                        deployment.failed_reason += f"\nK8s: {meta_str}"
                    else:
                        deployment.failed_reason = f"K8s: {meta_str}"

                    node_port = k8s_info.get("node_port")
                    if node_port:
                        deployment.deployed_url = f"http://localhost:{node_port}/"
                except Exception:
                    # Real Kubernetes integration is best-effort; ignore errors so deployments still succeed
                    pass

            try:
                await trigger_jenkins_build(deployment, project)
            except Exception:
                pass

            if pipeline and pipeline.pipeline_start_time is not None:
                total_duration = time.time() - pipeline.pipeline_start_time
                await pipeline._log_stage_complete(
                    "SCM_CHECKOUT",
                    total_duration,
                    JenkinsStylePipeline.STAGES.get("SCM_CHECKOUT", {}),
                )

            await _finalize_deployment(session, deployment, success=True)
            await session.commit()
        except Exception as exc:  # pragma: no cover
            await session.rollback()
            reason = f"Unexpected error: {exc}"
            deployment.failed_reason = reason
            await _append_log(session, deployment_id, reason, "error")
            if pipeline is not None:
                await pipeline._log_stage_failed(
                    "SCM_CHECKOUT",
                    reason,
                    JenkinsStylePipeline.STAGES.get("SCM_CHECKOUT", {}),
                )
            await _finalize_deployment(session, deployment, success=False)
            await session.commit()
        finally:
            if repo_dir.exists():
                shutil.rmtree(repo_dir, ignore_errors=True)
            _clear_cancel_flag(deployment_id)


async def enqueue_deployment(deployment_id: uuid.UUID) -> None:
    # Fire-and-forget background task
    asyncio.create_task(run_deployment_job(deployment_id))
