"""
PulseTrace Backend — Pydantic Validation Schemas

These schemas define the contract between:
  • Agent → Backend (Create schemas)
  • Backend → Dashboard (Response schemas)

All schemas use Pydantic v2 with strict validation, sensible
defaults, and clear field descriptions for OpenAPI documentation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ============================================================
# System Metrics
# ============================================================


class SystemMetricCreate(BaseModel):
    """Inbound system metrics from the monitoring agent.

    The agent sends one of these per collection interval.
    """

    hostname: str = Field(..., max_length=255, description="Source machine hostname")
    collected_at: datetime = Field(..., description="When metrics were collected (ISO 8601)")

    # CPU
    cpu_percent: Optional[float] = Field(None, ge=0, le=100, description="Overall CPU usage %")
    cpu_per_core: Optional[dict[str, float]] = Field(None, description="Per-core CPU percentages")
    cpu_freq_mhz: Optional[float] = Field(None, ge=0, description="Current CPU frequency in MHz")

    # Load averages
    load_avg_1: Optional[float] = Field(None, ge=0, description="1-minute load average")
    load_avg_5: Optional[float] = Field(None, ge=0, description="5-minute load average")
    load_avg_15: Optional[float] = Field(None, ge=0, description="15-minute load average")

    # Memory
    memory_total: Optional[int] = Field(None, ge=0, description="Total RAM in bytes")
    memory_used: Optional[int] = Field(None, ge=0, description="Used RAM in bytes")
    memory_available: Optional[int] = Field(None, ge=0, description="Available RAM in bytes")
    memory_percent: Optional[float] = Field(None, ge=0, le=100, description="RAM usage %")
    swap_total: Optional[int] = Field(None, ge=0, description="Total swap in bytes")
    swap_used: Optional[int] = Field(None, ge=0, description="Used swap in bytes")
    swap_percent: Optional[float] = Field(None, ge=0, le=100, description="Swap usage %")

    # Disk
    disk_total: Optional[int] = Field(None, ge=0, description="Total disk in bytes")
    disk_used: Optional[int] = Field(None, ge=0, description="Used disk in bytes")
    disk_free: Optional[int] = Field(None, ge=0, description="Free disk in bytes")
    disk_percent: Optional[float] = Field(None, ge=0, le=100, description="Disk usage %")
    disk_read_bytes: Optional[int] = Field(None, ge=0, description="Cumulative disk reads")
    disk_write_bytes: Optional[int] = Field(None, ge=0, description="Cumulative disk writes")

    # Network
    net_bytes_sent: Optional[int] = Field(None, ge=0, description="Cumulative bytes sent")
    net_bytes_recv: Optional[int] = Field(None, ge=0, description="Cumulative bytes received")
    net_packets_sent: Optional[int] = Field(None, ge=0, description="Cumulative packets sent")
    net_packets_recv: Optional[int] = Field(None, ge=0, description="Cumulative packets received")
    net_errin: Optional[int] = Field(0, ge=0, description="Inbound errors")
    net_errout: Optional[int] = Field(0, ge=0, description="Outbound errors")
    net_dropin: Optional[int] = Field(0, ge=0, description="Inbound drops")
    net_dropout: Optional[int] = Field(0, ge=0, description="Outbound drops")

    # Thermal
    cpu_temp_current: Optional[float] = Field(None, description="Current CPU temperature °C")
    cpu_temp_high: Optional[float] = Field(None, description="High threshold °C")
    cpu_temp_critical: Optional[float] = Field(None, description="Critical threshold °C")
    cpu_throttled: Optional[bool] = Field(None, description="Whether CPU is thermally throttled")

    # Extensibility
    extra: Optional[dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class SystemMetricResponse(SystemMetricCreate):
    """System metric returned from API queries."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


# ============================================================
# Process Metrics
# ============================================================


class ProcessMetricCreate(BaseModel):
    """Inbound process metrics from the monitoring agent."""

    hostname: str = Field(..., max_length=255)
    collected_at: datetime

    pid: int = Field(..., ge=0, description="Process ID")
    name: Optional[str] = Field(None, max_length=255, description="Process name")
    username: Optional[str] = Field(None, max_length=255, description="Process owner")
    status: Optional[str] = Field(None, max_length=50, description="Process status")
    cpu_percent: Optional[float] = Field(None, ge=0, description="Process CPU %")
    memory_percent: Optional[float] = Field(None, ge=0, le=100, description="Process memory %")
    memory_rss: Optional[int] = Field(None, ge=0, description="Resident set size in bytes")
    num_threads: Optional[int] = Field(None, ge=0, description="Thread count")
    command: Optional[str] = Field(None, description="Full command line")


class ProcessMetricResponse(ProcessMetricCreate):
    """Process metric returned from API queries."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


# ============================================================
# Batch Submission
# ============================================================


class MetricsBatch(BaseModel):
    """Batch of metrics sent by the agent in a single POST.

    The agent collects all metric types and sends them together
    for efficiency.
    """

    system: SystemMetricCreate = Field(..., description="System-level metrics")
    processes: List[ProcessMetricCreate] = Field(
        default_factory=list, description="Top N process metrics"
    )


class MetricsBatchResponse(BaseModel):
    """Acknowledgement after successful metric ingestion."""

    status: str = "accepted"
    system_metric_id: int = Field(..., description="Stored system metric ID")
    process_metrics_count: int = Field(..., description="Number of process metrics stored")
    alerts_generated: int = Field(0, description="Number of alerts triggered")


# ============================================================
# Alerts
# ============================================================


class AlertResponse(BaseModel):
    """Alert returned from API queries."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    hostname: str
    severity: str
    category: str
    message: str
    metric_value: Optional[float]
    threshold: Optional[float]
    source: str
    resolved: bool
    created_at: datetime
    resolved_at: Optional[datetime]


class AlertResolveResponse(BaseModel):
    """Response after resolving an alert."""

    id: int
    resolved: bool = True
    resolved_at: datetime


# ============================================================
# Health Check
# ============================================================


class HealthResponse(BaseModel):
    """Application health check response."""

    status: str = Field(..., description="Overall status: healthy or degraded")
    version: str = Field(..., description="Application version")
    database: dict = Field(..., description="Database connectivity info")
    uptime_seconds: float = Field(..., description="Seconds since startup")


# ============================================================
# Query Parameters
# ============================================================


class MetricsQuery(BaseModel):
    """Query parameters for filtering metrics."""

    hostname: Optional[str] = Field(None, description="Filter by hostname")
    minutes: int = Field(60, ge=1, le=10080, description="Lookback window in minutes")
    limit: int = Field(100, ge=1, le=1000, description="Max results to return")
    offset: int = Field(0, ge=0, description="Pagination offset")


class AlertsQuery(BaseModel):
    """Query parameters for filtering alerts."""

    hostname: Optional[str] = Field(None, description="Filter by hostname")
    severity: Optional[str] = Field(None, description="Filter by severity")
    category: Optional[str] = Field(None, description="Filter by category")
    resolved: Optional[bool] = Field(None, description="Filter by resolution status")
    limit: int = Field(50, ge=1, le=500, description="Max results to return")
    offset: int = Field(0, ge=0, description="Pagination offset")
