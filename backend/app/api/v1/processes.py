"""
PulseTrace Backend — Processes API Endpoints

Exposes process-level metrics stored by the monitoring agent.

GET /processes        — Query historical process metrics
GET /processes/latest — Latest snapshot: top N processes by CPU per host
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.schemas.metrics import ProcessMetricResponse
from app.services.metric_service import MetricService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/processes", tags=["Processes"])


@router.get(
    "",
    response_model=List[ProcessMetricResponse],
    summary="Query Process Metrics",
    description="Query historical per-process metrics with optional filters.",
)
async def get_process_metrics(
    hostname: Optional[str] = Query(None, description="Filter by hostname"),
    minutes: int = Query(5, ge=1, le=1440, description="Lookback window in minutes"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: AsyncSession = Depends(get_db),
) -> List[ProcessMetricResponse]:
    """
    Return process metrics ordered by collection time (newest first).

    The default lookback is 5 minutes (one collection cycle) to return
    a near-real-time process list without large payloads.
    """
    service = MetricService(db)
    records = await service.get_process_metrics(
        hostname=hostname,
        minutes=minutes,
        limit=limit,
        offset=offset,
    )
    return [ProcessMetricResponse.model_validate(r) for r in records]


@router.get(
    "/latest",
    response_model=List[ProcessMetricResponse],
    summary="Latest Process Snapshot",
    description="Get the most recent batch of process metrics per host, "
                "sorted by CPU usage descending.",
)
async def get_latest_processes(
    hostname: Optional[str] = Query(None, description="Filter by hostname"),
    limit: int = Query(25, ge=1, le=200, description="Number of top processes to return"),
    db: AsyncSession = Depends(get_db),
) -> List[ProcessMetricResponse]:
    """
    Return the freshest process rows collected across all (or one) host,
    ordered by CPU % descending so the heaviest processes are first.
    """
    service = MetricService(db)
    # Fetch the last 2 minutes — guaranteed to contain the latest batch
    records = await service.get_process_metrics(
        hostname=hostname,
        minutes=2,
        limit=limit,
    )
    # Sort in Python: CPU % descending (already limited by DB query)
    sorted_records = sorted(
        records,
        key=lambda r: (r.cpu_percent or 0.0),
        reverse=True,
    )
    return [ProcessMetricResponse.model_validate(r) for r in sorted_records[:limit]]
