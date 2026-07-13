"""
PulseTrace Backend — Health Check Endpoint

Provides a comprehensive health check that verifies:
  • Application is running
  • Database is reachable
  • Reports uptime and version

Used by Docker health checks, load balancers, and monitoring.
"""

from __future__ import annotations

import time

from fastapi import APIRouter

from app.config import settings
from app.database.connection import check_db_health
from app.schemas.metrics import HealthResponse

router = APIRouter(tags=["Health"])

# Track application start time for uptime calculation
_start_time = time.monotonic()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Returns application health status including database connectivity.",
)
async def health_check() -> HealthResponse:
    """Check application and database health."""
    db_health = await check_db_health()
    uptime = time.monotonic() - _start_time

    overall_status = "healthy" if db_health["status"] == "healthy" else "degraded"

    return HealthResponse(
        status=overall_status,
        version=settings.app_version,
        database=db_health,
        uptime_seconds=round(uptime, 2),
    )
