from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import DeploymentStage

StageKey = Literal[
    "queued",
    "cloning",
    "checkout",
    "installing",
    "building",
    "copying",
    "success",
    "failed",
    "cancelled",
]
StageStatus = Literal["pending", "in_progress", "completed", "failed", "cancelled"]

STAGE_LABELS: dict[StageKey, str] = {
    "queued": "Queued",
    "cloning": "Cloning",
    "checkout": "Checkout",
    "installing": "Installing",
    "building": "Building",
    "copying": "Copying",
    "success": "Success",
    "failed": "Failed",
    "cancelled": "Cancelled",
}

STAGE_ORDER = [
    "Queued",
    "Cloning",
    "Checkout",
    "Installing",
    "Building",
    "Copying",
    "Success",
    "Failed",
    "Cancelled",
]

STAGE_ORDER_INDEX = {name: idx for idx, name in enumerate(STAGE_ORDER)}


async def set_stage_status(
    session: AsyncSession,
    deployment_id: uuid.UUID,
    stage_key: StageKey,
    status: StageStatus,
) -> None:
    stage_name = STAGE_LABELS[stage_key]
    result = await session.execute(
        select(DeploymentStage).where(
            DeploymentStage.deployment_id == deployment_id,
            DeploymentStage.stage_name == stage_name,
        )
    )
    stage = result.scalar_one_or_none()
    now = datetime.utcnow()
    if stage is None:
        stage = DeploymentStage(
            deployment_id=deployment_id,
            stage_name=stage_name,
            status=status,
            started_at=now if status != "pending" else None,
        )
        session.add(stage)
    else:
        stage.status = status
        if status == "in_progress" and stage.started_at is None:
            stage.started_at = now

    if status in {"completed", "failed", "cancelled"}:
        if stage.started_at is None:
            stage.started_at = now
        stage.completed_at = now

    await session.flush()


def order_stages(stages: list[DeploymentStage]) -> list[DeploymentStage]:
    return sorted(
        stages,
        key=lambda s: (
            STAGE_ORDER_INDEX.get(s.stage_name, len(STAGE_ORDER)),
            s.started_at or s.created_at,
        ),
    )

