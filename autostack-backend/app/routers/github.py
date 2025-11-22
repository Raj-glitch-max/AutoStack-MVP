from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..db import get_db
from ..errors import ApiError
from ..models import GithubConnection, User
from ..schemas import (
    GithubBranch,
    GithubBranchesResponse,
    GithubConnectionStatus,
    GithubRepo,
    GithubReposResponse,
    DockerfileDetectionResponse,
)
from ..security import get_current_user


router = APIRouter(prefix="/api/github", tags=["github"])


async def _get_connection(db: AsyncSession, user_id) -> GithubConnection | None:
    result = await db.execute(select(GithubConnection).where(GithubConnection.user_id == user_id))
    return result.scalar_one_or_none()


@router.get("/connection", response_model=GithubConnectionStatus)
async def get_connection_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GithubConnectionStatus:
    conn = await _get_connection(db, current_user.id)
    if not conn:
        return GithubConnectionStatus(connected=False, username=None, avatar_url=current_user.avatar_url, scope=None, connected_at=None)

    return GithubConnectionStatus(
        connected=True,
        username=conn.github_username,
        avatar_url=current_user.avatar_url,
        scope=conn.scope,
        connected_at=conn.connected_at,
    )


@router.get("/profile")
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return a simple GitHub profile representation for the connected account.

    This matches the shape expected by older frontend code that called
    `/api/github/profile` directly and prevents 404s from that path.
    """

    conn = await _get_connection(db, current_user.id)
    if not conn:
        raise ApiError("UNAUTHORIZED", "GitHub not connected", 401)

    login = conn.github_username or ""
    return {
        "login": login,
        "avatar_url": current_user.avatar_url,
        "html_url": f"https://github.com/{login}" if login else "https://github.com",
    }


@router.post("/connect", response_model=GithubConnectionStatus)
async def connect_github(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GithubConnectionStatus:
    # Actual linking is handled via /auth/github OAuth; this endpoint simply returns current status.
    return await get_connection_status(current_user=current_user, db=db)


@router.delete("/disconnect")
async def disconnect_github(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    conn = await _get_connection(db, current_user.id)
    if conn:
        await db.delete(conn)
        await db.commit()
    return {"success": True}


@router.get("/repos", response_model=GithubReposResponse)
async def list_repos(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GithubReposResponse:
    conn = await _get_connection(db, current_user.id)
    if not conn:
        raise ApiError("UNAUTHORIZED", "GitHub not connected", 401)

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.github.com/user/repos",
            headers={"Authorization": f"token {conn.github_access_token}"},
            params={"per_page": 100},
            timeout=30,
        )
        if resp.status_code == 401:
            raise ApiError("UNAUTHORIZED", "Invalid GitHub token", 401)
        data = resp.json()

    repos = [
        GithubRepo(
            id=repo["id"],
            name=repo["name"],
            full_name=repo["full_name"],
            private=repo.get("private", False),
            default_branch=repo.get("default_branch", "main"),
        )
        for repo in data
    ]
    return GithubReposResponse(repos=repos)


@router.get("/repos/{repo_path:path}/branches", response_model=GithubBranchesResponse)
async def list_branches(
    repo_path: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GithubBranchesResponse:
    conn = await _get_connection(db, current_user.id)
    if not conn:
        raise ApiError("UNAUTHORIZED", "GitHub not connected", 401)

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://api.github.com/repos/{repo_path}/branches",
            headers={"Authorization": f"token {conn.github_access_token}"},
            timeout=30,
        )
        if resp.status_code == 404:
            raise ApiError("NOT_FOUND", "Repository not found", 404)
        if resp.status_code == 401:
            raise ApiError("UNAUTHORIZED", "Invalid GitHub token", 401)
        data = resp.json()

    branches = [GithubBranch(name=item["name"]) for item in data]
    return GithubBranchesResponse(branches=branches)


@router.get("/dockerfile", response_model=DockerfileDetectionResponse)
async def detect_dockerfile(
    repository: str,
    branch: str = "main",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DockerfileDetectionResponse:
    """Check if the given GitHub repository/branch has a Dockerfile at the repo root.

    This is used by the deployment UI to decide whether to prefer a Docker-based runtime
    or the default static build pipeline.
    """

    conn = await _get_connection(db, current_user.id)
    if not conn:
        raise ApiError("UNAUTHORIZED", "GitHub not connected", 401)

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://api.github.com/repos/{repository}/contents/Dockerfile",
            headers={"Authorization": f"token {conn.github_access_token}"},
            params={"ref": branch},
            timeout=30,
        )

    if resp.status_code == 404:
        return DockerfileDetectionResponse(has_dockerfile=False, path=None)
    if resp.status_code == 401:
        raise ApiError("UNAUTHORIZED", "Invalid GitHub token", 401)

    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict) and data.get("type") == "file":
        return DockerfileDetectionResponse(has_dockerfile=True, path=data.get("path"))

    return DockerfileDetectionResponse(has_dockerfile=False, path=None)


@router.get("/webhook-info")
async def get_webhook_info(
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    base = str(settings.backend_url).rstrip("/")
    url = f"{base}/webhook/github"
    return {
        "url": url,
        "secret": settings.github_webhook_secret,
    }
