"""
PulseTrace Backend — Metrics API Endpoints

Handles metric ingestion from agents and metric queries
from the dashboard. All endpoints are versioned under /api/v1/.

POST /metrics  — Agent pushes metrics here
GET  /metrics  — Dashboard queries historical metrics
GET  /metrics/latest — Dashboard gets latest snapshot per host
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.schemas.metrics import (
    MetricsBatch,
    MetricsBatchResponse,
    SystemMetricResponse,
)
from app.services.metric_service import MetricService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.post(
    "",
    response_model=MetricsBatchResponse,
    status_code=201,
    summary="Ingest Metrics Batch",
    description="Accepts a batch of system and process metrics from the monitoring agent.",
)
async def ingest_metrics(
    batch: MetricsBatch,
    db: AsyncSession = Depends(get_db),
) -> MetricsBatchResponse:
    """Ingest a metrics batch from the monitoring agent.

    The agent sends system-level metrics and top N process metrics
    in a single request for efficiency. The backend validates,
    stores, and checks alert thresholds.
    """
    try:
        service = MetricService(db)
        return await service.ingest_batch(batch)
    except Exception as exc:
        logger.error("Failed to ingest metrics: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to ingest metrics: {str(exc)}",
        )


@router.get(
    "",
    response_model=List[SystemMetricResponse],
    summary="Query Metrics",
    description="Query historical system metrics with optional filters.",
)
async def get_metrics(
    hostname: Optional[str] = Query(None, description="Filter by hostname"),
    minutes: int = Query(60, ge=1, le=10080, description="Lookback window in minutes"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: AsyncSession = Depends(get_db),
) -> List[SystemMetricResponse]:
    """Query system metrics with time range and hostname filters."""
    service = MetricService(db)
    metrics = await service.get_metrics(
        hostname=hostname,
        minutes=minutes,
        limit=limit,
        offset=offset,
    )
    return [SystemMetricResponse.model_validate(m) for m in metrics]


@router.get(
    "/latest",
    response_model=List[SystemMetricResponse],
    summary="Latest Metrics",
    description="Get the most recent metric snapshot for each reporting host.",
)
async def get_latest_metrics(
    hostname: Optional[str] = Query(None, description="Filter by hostname"),
    db: AsyncSession = Depends(get_db),
) -> List[SystemMetricResponse]:
    """Get the latest metric snapshot per hostname."""
    service = MetricService(db)
    metrics = await service.get_latest_metrics(hostname=hostname)
    return [SystemMetricResponse.model_validate(m) for m in metrics]
