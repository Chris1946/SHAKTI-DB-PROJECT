"""
PulseTrace Backend — FastAPI Application Factory

This is the entry point for the FastAPI application. It:
  • Configures CORS middleware
  • Optionally enables API key authentication
  • Manages application lifecycle (startup/shutdown)
  • Mounts the versioned API router
  • Configures structured logging

Start with:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.v1.router import router as v1_router
from app.config import settings
from app.database.connection import dispose_engine

# ============================================================
# Logging Configuration
# ============================================================

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)

logger = logging.getLogger("pulsetrace")


# ============================================================
# API Key Middleware
# ============================================================


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Validates X-API-Key header on non-health endpoints.

    Skipped entirely when settings.api_key is empty.
    """

    EXEMPT_PATHS = {"/api/v1/health", "/docs", "/redoc", "/openapi.json"}

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip auth for exempt paths
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        # Skip if API key auth is disabled
        if not settings.api_key_enabled:
            return await call_next(request)

        # Validate API key
        api_key = request.headers.get("X-API-Key", "")
        if api_key != settings.api_key:
            logger.warning(
                "Unauthorized request from %s to %s",
                request.client.host if request.client else "unknown",
                request.url.path,
            )
            return Response(
                content='{"detail":"Invalid or missing API key"}',
                status_code=401,
                media_type="application/json",
            )

        return await call_next(request)


# ============================================================
# Application Lifecycle
# ============================================================


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown.

    Startup:
      - Log configuration summary
      - Database connection pool is created lazily by SQLAlchemy

    Shutdown:
      - Dispose database connection pool
    """
    logger.info("=" * 60)
    logger.info("PulseTrace Backend v%s starting", settings.app_version)
    logger.info("Database: %s", settings.database_url.split("@")[-1])
    logger.info("API Key Auth: %s", "ENABLED" if settings.api_key_enabled else "DISABLED")
    logger.info("Log Level: %s", settings.log_level)
    logger.info("=" * 60)

    yield

    logger.info("PulseTrace Backend shutting down...")
    await dispose_engine()
    logger.info("Shutdown complete")


# ============================================================
# Application Factory
# ============================================================

app = FastAPI(
    title="PulseTrace API",
    description=(
        "AI-Powered eBPF Latency Analyzer & Root Cause Detection Platform. "
        "Collects system metrics, detects anomalies, and provides actionable insights."
    ),
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ---- Middleware ----

# CORS: Allow dashboard and development origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Key authentication (conditional)
app.add_middleware(APIKeyMiddleware)

# ---- Routes ----
app.include_router(v1_router)


# ---- Root redirect ----
@app.get("/", include_in_schema=False)
async def root():
    """Redirect root to API docs."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/api/v1/health",
    }
