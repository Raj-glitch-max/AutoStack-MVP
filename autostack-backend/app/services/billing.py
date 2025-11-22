from __future__ import annotations

from datetime import datetime
from typing import Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Deployment, Project, User


PIPELINE_RATE_PER_MINUTE = 0.002


async def calculate_billing(db: AsyncSession, user: User) -> Dict:
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    query = (
        select(Deployment, Project)
        .join(Project, Deployment.project_id == Project.id)
        .where(
            Deployment.user_id == user.id,
            Deployment.is_deleted.is_(False),
            Deployment.created_at >= month_start,
        )
    )
    result = await db.execute(query)
    rows = result.all()

    projects: Dict[str, Dict] = {}
    for dep, proj in rows:
        key = str(proj.id)
        item = projects.get(key)
        if not item:
            item = {
                "project_id": key,
                "name": proj.name,
                "total_deployments": 0,
                "successful_deployments": 0,
                "pipeline_minutes": 0.0,
                "estimated_cost": 0.0,
            }
            projects[key] = item

        item["total_deployments"] += 1
        if dep.status == "success":
            item["successful_deployments"] += 1
        duration_seconds = dep.build_duration_seconds or 0
        minutes = duration_seconds / 60.0
        item["pipeline_minutes"] += minutes
        item["estimated_cost"] += minutes * PIPELINE_RATE_PER_MINUTE

    total_cost = sum(p["estimated_cost"] for p in projects.values())

    day = now.day
    days_in_month = 30
    if day > 0:
        factor = days_in_month / float(day)
    else:
        factor = 1.0
    projected = total_cost * factor

    return {
        "currency": "USD",
        "total_month_to_date": total_cost,
        "projected_monthly": projected,
        "last_updated": now,
        "projects": list(projects.values()),
    }
