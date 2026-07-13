"""
PulseTrace Backend — Alerts API Endpoints

Provides read and management operations for alerts generated
by the rule engine and (future) AI anomaly detection.

GET   /alerts           — List alerts with filters
PATCH /alerts/{id}/resolve — Mark an alert as resolved
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.schemas.metrics import AlertResponse, AlertResolveResponse
from app.services.metric_service import MetricService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get(
    "",
    response_model=List[AlertResponse],
    summary="List Alerts",
    description="Query alerts with optional filters for hostname, severity, category, and resolution status.",
)
async def get_alerts(
    hostname: Optional[str] = Query(None, description="Filter by hostname"),
    severity: Optional[str] = Query(None, description="Filter: critical, warning, info"),
    category: Optional[str] = Query(None, description="Filter: cpu, memory, disk, network"),
    resolved: Optional[bool] = Query(None, description="Filter by resolution status"),
    limit: int = Query(50, ge=1, le=500, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: AsyncSession = Depends(get_db),
) -> List[AlertResponse]:
    """List alerts with optional filters."""
    service = MetricService(db)
    alerts = await service.get_alerts(
        hostname=hostname,
        severity=severity,
        category=category,
        resolved=resolved,
        limit=limit,
        offset=offset,
    )
    return [AlertResponse.model_validate(a) for a in alerts]


@router.patch(
    "/{alert_id}/resolve",
    response_model=AlertResolveResponse,
    summary="Resolve Alert",
    description="Mark an alert as resolved. Sets resolved=true and records the resolution timestamp.",
)
async def resolve_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
) -> AlertResolveResponse:
    """Mark an alert as resolved."""
    service = MetricService(db)
    alert = await service.resolve_alert(alert_id)

    if alert is None:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

    return AlertResolveResponse(
        id=alert.id,
        resolved=alert.resolved,
        resolved_at=alert.resolved_at,
    )
