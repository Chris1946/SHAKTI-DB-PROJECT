"""
PulseTrace Backend — Metric Service (Business Logic)

This service layer sits between the API routes and the database.
It handles:
  • Metric ingestion (validate → store → check thresholds)
  • Metric queries (time range, hostname, pagination)
  • Rule-based alert generation
  • Alert management

All database operations use async SQLAlchemy sessions injected
by FastAPI's dependency system.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Sequence

from sqlalchemy import select, update, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.metrics import Alert, ProcessMetric, SystemMetric
from app.schemas.metrics import (
    MetricsBatch,
    MetricsBatchResponse,
    SystemMetricCreate,
    ProcessMetricCreate,
)

logger = logging.getLogger(__name__)


# ============================================================
# Alert Threshold Rules
# ============================================================

# Rules are defined as tuples: (category, field, warning_threshold, critical_threshold, message_template)
# This makes it trivial to add new rules without modifying logic.
ALERT_RULES = [
    (
        "cpu",
        "cpu_percent",
        settings.alert_cpu_warning,
        settings.alert_cpu_critical,
        "CPU usage at {value:.1f}% (threshold: {threshold:.1f}%)",
    ),
    (
        "memory",
        "memory_percent",
        settings.alert_memory_warning,
        settings.alert_memory_critical,
        "Memory usage at {value:.1f}% (threshold: {threshold:.1f}%)",
    ),
    (
        "disk",
        "disk_percent",
        settings.alert_disk_warning,
        settings.alert_disk_critical,
        "Disk usage at {value:.1f}% (threshold: {threshold:.1f}%)",
    ),
]


class MetricService:
    """Handles all metric-related business logic."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # --------------------------------------------------------
    # Ingestion
    # --------------------------------------------------------

    async def ingest_batch(self, batch: MetricsBatch) -> MetricsBatchResponse:
        """Ingest a batch of metrics from the monitoring agent.

        Steps:
          1. Store system metrics
          2. Store process metrics
          3. Check alert thresholds
          4. Return acknowledgement

        Args:
            batch: Validated metrics batch from the agent.

        Returns:
            MetricsBatchResponse with stored IDs and alert count.
        """
        # 1. Store system metrics
        system_metric = await self._store_system_metric(batch.system)

        # 2. Store process metrics
        process_count = await self._store_process_metrics(batch.processes)

        # 3. Check thresholds and generate alerts
        alerts_count = await self._check_thresholds(batch.system)

        # Commit all changes in a single transaction
        await self.db.commit()

        logger.info(
            "Ingested metrics from %s: system_id=%d, processes=%d, alerts=%d",
            batch.system.hostname,
            system_metric.id,
            process_count,
            alerts_count,
        )

        return MetricsBatchResponse(
            status="accepted",
            system_metric_id=system_metric.id,
            process_metrics_count=process_count,
            alerts_generated=alerts_count,
        )

    async def _store_system_metric(self, data: SystemMetricCreate) -> SystemMetric:
        """Store a single system metric record."""
        metric = SystemMetric(**data.model_dump())
        self.db.add(metric)
        await self.db.flush()  # Get the ID without committing
        return metric

    async def _store_process_metrics(
        self, processes: List[ProcessMetricCreate]
    ) -> int:
        """Store process metric records in bulk."""
        if not processes:
            return 0

        process_models = [ProcessMetric(**p.model_dump()) for p in processes]
        self.db.add_all(process_models)
        await self.db.flush()
        return len(process_models)

    async def _check_thresholds(self, data: SystemMetricCreate) -> int:
        """Check metric values against alert thresholds.

        Generates alerts for any threshold violations. Uses a
        deduplication window to avoid alert storms — won't create
        a new alert if one already exists for the same category
        within the last 5 minutes.

        Returns:
            Number of alerts generated.
        """
        alerts_generated = 0
        dedup_window = datetime.now(timezone.utc) - timedelta(minutes=5)

        for category, field, warning_thresh, critical_thresh, msg_template in ALERT_RULES:
            value = getattr(data, field, None)
            if value is None:
                continue

            # Determine severity
            if value >= critical_thresh:
                severity = "critical"
                threshold = critical_thresh
            elif value >= warning_thresh:
                severity = "warning"
                threshold = warning_thresh
            else:
                continue  # No alert needed

            # Deduplication: skip if recent unresolved alert exists
            existing = await self.db.execute(
                select(Alert.id).where(
                    and_(
                        Alert.hostname == data.hostname,
                        Alert.category == category,
                        Alert.resolved == False,  # noqa: E712
                        Alert.created_at >= dedup_window,
                    )
                ).limit(1)
            )
            if existing.scalar() is not None:
                continue

            # Create alert
            alert = Alert(
                hostname=data.hostname,
                severity=severity,
                category=category,
                message=msg_template.format(value=value, threshold=threshold),
                metric_value=value,
                threshold=threshold,
                source="rule_engine",
            )
            self.db.add(alert)
            alerts_generated += 1

            logger.warning(
                "Alert generated: %s %s on %s — %s",
                severity.upper(),
                category,
                data.hostname,
                alert.message,
            )

        return alerts_generated

    # --------------------------------------------------------
    # Queries
    # --------------------------------------------------------

    async def get_metrics(
        self,
        hostname: Optional[str] = None,
        minutes: int = 60,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[SystemMetric]:
        """Query system metrics with optional filters.

        Args:
            hostname: Filter by specific host.
            minutes: Lookback window from now.
            limit: Maximum number of results.
            offset: Pagination offset.

        Returns:
            List of SystemMetric records ordered by time descending.
        """
        since = datetime.now(timezone.utc) - timedelta(minutes=minutes)

        query = (
            select(SystemMetric)
            .where(SystemMetric.collected_at >= since)
            .order_by(SystemMetric.collected_at.desc())
            .limit(limit)
            .offset(offset)
        )

        if hostname:
            query = query.where(SystemMetric.hostname == hostname)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_latest_metrics(
        self,
        hostname: Optional[str] = None,
    ) -> Sequence[SystemMetric]:
        """Get the most recent metric snapshot per hostname.

        Uses a window function to efficiently select only the
        latest row per host.
        """
        # Subquery to find max collected_at per hostname
        subq = (
            select(
                SystemMetric.hostname,
                func.max(SystemMetric.collected_at).label("max_time"),
            )
            .group_by(SystemMetric.hostname)
        )

        if hostname:
            subq = subq.where(SystemMetric.hostname == hostname)

        subq = subq.subquery()

        query = select(SystemMetric).join(
            subq,
            and_(
                SystemMetric.hostname == subq.c.hostname,
                SystemMetric.collected_at == subq.c.max_time,
            ),
        )

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_process_metrics(
        self,
        hostname: Optional[str] = None,
        minutes: int = 60,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[ProcessMetric]:
        """Query process metrics with optional filters."""
        since = datetime.now(timezone.utc) - timedelta(minutes=minutes)

        query = (
            select(ProcessMetric)
            .where(ProcessMetric.collected_at >= since)
            .order_by(ProcessMetric.collected_at.desc())
            .limit(limit)
            .offset(offset)
        )

        if hostname:
            query = query.where(ProcessMetric.hostname == hostname)

        result = await self.db.execute(query)
        return result.scalars().all()

    # --------------------------------------------------------
    # Alerts
    # --------------------------------------------------------

    async def get_alerts(
        self,
        hostname: Optional[str] = None,
        severity: Optional[str] = None,
        category: Optional[str] = None,
        resolved: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Alert]:
        """Query alerts with optional filters."""
        query = (
            select(Alert)
            .order_by(Alert.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        if hostname:
            query = query.where(Alert.hostname == hostname)
        if severity:
            query = query.where(Alert.severity == severity)
        if category:
            query = query.where(Alert.category == category)
        if resolved is not None:
            query = query.where(Alert.resolved == resolved)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def resolve_alert(self, alert_id: int) -> Optional[Alert]:
        """Mark an alert as resolved.

        Returns:
            The updated Alert, or None if not found.
        """
        now = datetime.now(timezone.utc)

        await self.db.execute(
            update(Alert)
            .where(Alert.id == alert_id)
            .values(resolved=True, resolved_at=now)
        )
        await self.db.commit()

        result = await self.db.execute(
            select(Alert).where(Alert.id == alert_id)
        )
        return result.scalar_one_or_none()
