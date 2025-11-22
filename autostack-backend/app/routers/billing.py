from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import User
from ..schemas import BillingProjectBreakdown, BillingSummary, BillingSummaryResponse
from ..security import get_current_user
from ..services.billing import calculate_billing


router = APIRouter(prefix="/api/billing", tags=["billing"])


@router.get("/summary", response_model=BillingSummaryResponse)
async def get_billing_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BillingSummaryResponse:
    data = await calculate_billing(db, current_user)
    projects = [
        BillingProjectBreakdown(
            project_id=item["project_id"],
            name=item["name"],
            total_deployments=item["total_deployments"],
            successful_deployments=item["successful_deployments"],
            pipeline_minutes=item["pipeline_minutes"],
            estimated_cost=item["estimated_cost"],
        )
        for item in data["projects"]
    ]
    summary = BillingSummary(
        currency=data["currency"],
        total_month_to_date=data["total_month_to_date"],
        projected_monthly=data["projected_monthly"],
        last_updated=data["last_updated"],
        projects=projects,
    )
    return BillingSummaryResponse(billing=summary)
