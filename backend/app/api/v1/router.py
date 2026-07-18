"""
PulseTrace Backend — API v1 Router

Aggregates all v1 route groups under a single prefix.
New feature routes are added here as the project grows.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import alerts, health, metrics, processes, ai, intelligence

router = APIRouter(prefix="/api/v1")

# Mount route groups
router.include_router(health.router)
router.include_router(metrics.router)
router.include_router(processes.router)
router.include_router(alerts.router)
router.include_router(ai.router)
router.include_router(intelligence.router)
