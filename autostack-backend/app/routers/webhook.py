from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import Any

from fastapi import APIRouter, Header, Request, Response
from sqlalchemy import func, select

from ..build_engine import enqueue_deployment
from ..config import settings
from ..db import AsyncSessionLocal
from ..errors import ApiError
from ..models import Deployment, Project, User, WebhookPayload
from ..services.stages import set_stage_status


logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhook"])


def _verify_signature(secret: str, body: bytes, signature: str | None) -> None:
    if not signature or not signature.startswith("sha256="):
        raise ApiError("UNAUTHORIZED", "Missing or invalid webhook signature", 401)
    provided = signature.split("=", 1)[1]
    digest = hmac.new(secret.encode(), msg=body, digestmod=hashlib.sha256).hexdigest()
    if not hmac.compare_digest(digest, provided):
        raise ApiError("UNAUTHORIZED", "Invalid webhook signature", 401)


@router.post("/webhook/github")
async def github_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(None, alias="X-Hub-Signature-256"),
    x_github_event: str | None = Header(None, alias="X-GitHub-Event"),
) -> dict[str, Any]:
    body = await request.body()
    logger.debug("GitHub webhook payload: %s", body.decode(errors="ignore"))

    _verify_signature(settings.github_webhook_secret, body, x_hub_signature_256)

    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:  # pragma: no cover
        raise ApiError("VALIDATION_ERROR", f"Invalid JSON payload: {exc}", 400)

    async with AsyncSessionLocal() as db:
        payload_entry = WebhookPayload(
            provider="github",
            payload_json=payload,
            headers=dict(request.headers),
        )
        db.add(payload_entry)
        await db.flush()

        if x_github_event != "push":
            await db.commit()
            return Response(status_code=202)

        ref = payload.get("ref")
        repo = payload.get("repository", {})
        full_name = repo.get("full_name")

        if not ref or not full_name:
            await db.commit()
            raise ApiError("VALIDATION_ERROR", "Missing ref or repository metadata", 400)

        branch = ref.split("/")[-1]
        head_commit = payload.get("head_commit") or {}
        project_query = select(Project).where(func.lower(Project.repository) == func.lower(full_name))
        project = (await db.execute(project_query)).scalar_one_or_none()
        if not project:
            await db.commit()
            raise ApiError("NOT_FOUND", "No project configured for this repository", 404)

        if not project.auto_deploy_enabled:
            await db.commit()
            return {"status": "ignored", "reason": "auto_deploy_disabled"}

        target_branch = project.auto_deploy_branch or project.branch
        if target_branch and target_branch != branch:
            await db.commit()
            return {"status": "ignored", "reason": "branch_mismatch"}

        user = await db.get(User, project.user_id)
        if not user:
            await db.commit()
            raise ApiError("NOT_FOUND", "Project owner not found", 404)

        deployment = Deployment(
            project_id=project.id,
            user_id=user.id,
            status="queued",
            branch=branch,
            commit_hash=head_commit.get("id"),
            commit_message=head_commit.get("message"),
            author=(head_commit.get("author") or {}).get("name"),
            creator_type="webhook",
            is_production=True,
            env_vars=project.env_vars,
        )
        db.add(deployment)
        await db.flush()
        payload_entry.deployment_id = deployment.id
        await set_stage_status(db, deployment.id, "queued", "in_progress")

        await enqueue_deployment(deployment.id)
        await db.commit()

    return {"status": "queued", "deploymentId": str(deployment.id)}
