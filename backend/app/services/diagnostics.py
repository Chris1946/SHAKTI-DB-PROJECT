"""
PulseTrace Backend — Real-Time Diagnostic Engine
==================================================

Rule-based root cause analysis that examines actual system metrics
and process snapshots to determine WHY a system is slow.

Bottleneck categories:
  🔴 CPU Bound        — single process hogging cores / runaway computation
  🟡 Memory Pressure  — high mem usage, swap activity, potential thrashing
  🟠 I/O Bottleneck   — disk read/write bytes spiking far above baseline
  🔵 Network Saturation — high error rates, excessive bandwidth
  🌡️ Thermal Throttle — CPU temp > high threshold, frequency reduced
  🟣 Scheduler Contention — load average >> CPU core count

For each alert, the engine:
  1. Fetches system metrics ±2 minutes around the anomaly
  2. Computes 1-hour baseline statistics (mean, std)
  3. Classifies the bottleneck across 6 dimensions
  4. Identifies the top contributing processes
  5. Returns a structured diagnosis with human-readable explanation
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.metrics import Alert, ProcessMetric, SystemMetric

logger = logging.getLogger("diagnostics")


# ──────────────────────────────────────────────────────────────
# Data classes for results
# ──────────────────────────────────────────────────────────────

class BottleneckFinding:
    """A single bottleneck dimension with severity and evidence."""

    def __init__(
        self,
        category: str,
        icon: str,
        severity: float,  # 0.0 – 1.0
        summary: str,
        details: Dict[str, Any],
    ):
        self.category = category
        self.icon = icon
        self.severity = severity
        self.summary = summary
        self.details = details

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "icon": self.icon,
            "severity": round(self.severity, 2),
            "summary": self.summary,
            "details": self.details,
        }


class DiagnosticReport:
    """Full root cause analysis report."""

    def __init__(
        self,
        alert_id: int,
        primary_bottleneck: Optional[BottleneckFinding],
        all_findings: List[BottleneckFinding],
        top_processes: List[Dict[str, Any]],
        system_snapshot: Dict[str, Any],
        recommendation: str,
    ):
        self.alert_id = alert_id
        self.primary_bottleneck = primary_bottleneck
        self.all_findings = all_findings
        self.top_processes = top_processes
        self.system_snapshot = system_snapshot
        self.recommendation = recommendation

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "primary_bottleneck": self.primary_bottleneck.to_dict() if self.primary_bottleneck else None,
            "all_findings": [f.to_dict() for f in self.all_findings],
            "top_processes": self.top_processes,
            "system_snapshot": self.system_snapshot,
            "recommendation": self.recommendation,
        }


# ──────────────────────────────────────────────────────────────
# Diagnostic Engine
# ──────────────────────────────────────────────────────────────

class DiagnosticEngine:
    """
    Performs real root cause analysis by examining actual metrics
    and process data around an alert's timestamp.
    """

    # How many minutes of data to look at around the anomaly
    WINDOW_MINUTES = 2
    # Baseline period for computing mean/std
    BASELINE_MINUTES = 60
    # Number of CPU cores (used for scheduler contention)
    CPU_COUNT = os.cpu_count() or 4

    async def analyze(self, alert: Alert, db: AsyncSession) -> DiagnosticReport:
        """
        Run full diagnosis for the given alert.
        """
        alert_time = alert.created_at
        if alert_time.tzinfo is None:
            alert_time = alert_time.replace(tzinfo=timezone.utc)

        # 1. Fetch metrics around the anomaly
        window_start = alert_time - timedelta(minutes=self.WINDOW_MINUTES)
        window_end   = alert_time + timedelta(minutes=self.WINDOW_MINUTES)

        anomaly_metrics = await self._fetch_system_metrics(
            db, alert.hostname, window_start, window_end
        )

        # 2. Fetch baseline metrics (1 hour before)
        baseline_start = alert_time - timedelta(minutes=self.BASELINE_MINUTES)
        baseline_end   = alert_time - timedelta(minutes=self.WINDOW_MINUTES)

        baseline_metrics = await self._fetch_system_metrics(
            db, alert.hostname, baseline_start, baseline_end
        )

        # 3. Fetch process snapshot around the anomaly
        top_processes = await self._fetch_process_snapshot(
            db, alert.hostname, window_start, window_end
        )

        # 4. Compute baseline statistics
        baseline_stats = self._compute_stats(baseline_metrics)

        # 5. Compute anomaly-window averages
        anomaly_snapshot = self._compute_snapshot(anomaly_metrics)

        # 6. Run bottleneck classifiers
        findings: List[BottleneckFinding] = []

        findings.append(self._check_cpu_bound(anomaly_snapshot, baseline_stats, top_processes))
        findings.append(self._check_memory_pressure(anomaly_snapshot, baseline_stats, top_processes))
        findings.append(self._check_io_bottleneck(anomaly_snapshot, baseline_stats, top_processes))
        findings.append(self._check_network(anomaly_snapshot, baseline_stats))
        findings.append(self._check_thermal(anomaly_snapshot))
        findings.append(self._check_scheduler(anomaly_snapshot))

        # Filter to findings with severity > 0
        active_findings = [f for f in findings if f.severity > 0]
        active_findings.sort(key=lambda f: f.severity, reverse=True)

        primary = active_findings[0] if active_findings else None

        # 7. Generate recommendation
        recommendation = self._generate_recommendation(primary, top_processes)

        # 8. Format top processes for output
        proc_output = []
        for p in top_processes[:5]:
            proc_output.append({
                "pid": p.get("pid"),
                "name": p.get("name", "unknown"),
                "cpu_percent": round(p.get("cpu_percent", 0), 1),
                "memory_percent": round(p.get("memory_percent", 0), 1),
                "memory_rss_mb": round(p.get("memory_rss", 0) / (1024 * 1024), 1) if p.get("memory_rss") else 0,
                "threads": p.get("num_threads", 0),
                "command": p.get("command", ""),
            })

        return DiagnosticReport(
            alert_id=alert.id,
            primary_bottleneck=primary,
            all_findings=active_findings,
            top_processes=proc_output,
            system_snapshot=anomaly_snapshot,
            recommendation=recommendation,
        )

    # ──────────────────────────────────────────────────────────
    # Data fetching
    # ──────────────────────────────────────────────────────────

    async def _fetch_system_metrics(
        self, db: AsyncSession, hostname: str,
        start: datetime, end: datetime,
    ) -> List[Dict[str, Any]]:
        query = (
            select(SystemMetric)
            .where(SystemMetric.hostname == hostname)
            .where(SystemMetric.collected_at >= start)
            .where(SystemMetric.collected_at <= end)
            .order_by(SystemMetric.collected_at.asc())
        )
        result = await db.execute(query)
        rows = result.scalars().all()

        return [
            {
                "cpu_percent": float(r.cpu_percent or 0),
                "memory_percent": float(r.memory_percent or 0),
                "memory_used": int(r.memory_used or 0),
                "memory_total": int(r.memory_total or 1),
                "disk_percent": float(r.disk_percent or 0),
                "disk_read_bytes": int(r.disk_read_bytes or 0),
                "disk_write_bytes": int(r.disk_write_bytes or 0),
                "net_bytes_sent": int(r.net_bytes_sent or 0),
                "net_bytes_recv": int(r.net_bytes_recv or 0),
                "net_errin": int(r.net_errin or 0),
                "net_errout": int(r.net_errout or 0),
                "cpu_temp_current": float(r.cpu_temp_current) if r.cpu_temp_current else None,
                "cpu_temp_high": float(r.cpu_temp_high) if r.cpu_temp_high else None,
                "cpu_throttled": r.cpu_throttled,
                "load_avg_1": float(r.load_avg_1 or 0),
                "load_avg_5": float(r.load_avg_5 or 0),
                "swap_used": int(r.swap_used or 0),
                "swap_percent": float(r.swap_percent or 0),
                "cpu_freq_mhz": float(r.cpu_freq_mhz or 0),
            }
            for r in rows
        ]

    async def _fetch_process_snapshot(
        self, db: AsyncSession, hostname: str,
        start: datetime, end: datetime,
    ) -> List[Dict[str, Any]]:
        """Get the top processes by CPU during the anomaly window."""
        query = (
            select(ProcessMetric)
            .where(ProcessMetric.hostname == hostname)
            .where(ProcessMetric.collected_at >= start)
            .where(ProcessMetric.collected_at <= end)
            .order_by(ProcessMetric.cpu_percent.desc())
            .limit(20)
        )
        result = await db.execute(query)
        rows = result.scalars().all()

        # Deduplicate by PID, keeping the highest CPU reading
        seen_pids = set()
        unique = []
        for r in rows:
            if r.pid not in seen_pids:
                seen_pids.add(r.pid)
                unique.append({
                    "pid": r.pid,
                    "name": r.name,
                    "cpu_percent": float(r.cpu_percent or 0),
                    "memory_percent": float(r.memory_percent or 0),
                    "memory_rss": int(r.memory_rss or 0),
                    "num_threads": r.num_threads,
                    "command": r.command,
                })
        return unique

    # ──────────────────────────────────────────────────────────
    # Statistics
    # ──────────────────────────────────────────────────────────

    def _compute_stats(self, metrics: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        """Compute mean and std for each numeric metric."""
        if not metrics:
            return {}

        keys = [
            "cpu_percent", "memory_percent", "disk_percent",
            "disk_read_bytes", "disk_write_bytes",
            "net_bytes_sent", "net_bytes_recv",
            "load_avg_1", "swap_percent",
        ]
        stats = {}
        for k in keys:
            values = [m.get(k, 0) for m in metrics]
            n = len(values)
            if n == 0:
                stats[k] = {"mean": 0, "std": 0}
                continue
            mean = sum(values) / n
            variance = sum((v - mean) ** 2 for v in values) / max(n, 1)
            std = variance ** 0.5
            stats[k] = {"mean": mean, "std": std}

        return stats

    def _compute_snapshot(self, metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compute average values across the anomaly window."""
        if not metrics:
            return {}

        keys = [
            "cpu_percent", "memory_percent", "disk_percent",
            "disk_read_bytes", "disk_write_bytes",
            "net_bytes_sent", "net_bytes_recv", "net_errin", "net_errout",
            "load_avg_1", "load_avg_5", "swap_used", "swap_percent",
            "cpu_freq_mhz",
        ]
        snapshot = {}
        n = len(metrics)
        for k in keys:
            snapshot[k] = sum(m.get(k, 0) for m in metrics) / n

        # Non-averaged fields: take the latest value
        latest = metrics[-1]
        snapshot["cpu_temp_current"] = latest.get("cpu_temp_current")
        snapshot["cpu_temp_high"] = latest.get("cpu_temp_high")
        snapshot["cpu_throttled"] = latest.get("cpu_throttled")
        snapshot["memory_used"] = latest.get("memory_used", 0)
        snapshot["memory_total"] = latest.get("memory_total", 1)

        return snapshot

    # ──────────────────────────────────────────────────────────
    # Bottleneck classifiers
    # ──────────────────────────────────────────────────────────

    def _z_score(self, value: float, stats: Dict[str, float]) -> float:
        """How many standard deviations above the mean."""
        std = stats.get("std", 0)
        if std < 0.01:
            return 0.0
        return (value - stats.get("mean", 0)) / std

    def _check_cpu_bound(
        self, snap: Dict, baseline: Dict, processes: List[Dict],
    ) -> BottleneckFinding:
        cpu = snap.get("cpu_percent", 0)
        cpu_stats = baseline.get("cpu_percent", {"mean": 50, "std": 15})
        z = self._z_score(cpu, cpu_stats)

        # Find the top CPU hog
        top_proc = processes[0] if processes else {}
        top_cpu = top_proc.get("cpu_percent", 0)
        top_name = top_proc.get("name", "unknown")

        severity = 0.0
        if cpu > 85 and z > 1.5:
            severity = min(1.0, 0.4 + (z / 8))
        if top_cpu > 50:
            severity = min(1.0, severity + 0.3)
        if cpu > 95:
            severity = min(1.0, severity + 0.2)

        summary = ""
        if severity > 0:
            summary = (
                f"CPU is at {cpu:.0f}% ({z:.1f}σ above baseline). "
                f"Top consumer: '{top_name}' using {top_cpu:.0f}% CPU."
            )

        return BottleneckFinding(
            category="CPU Bound",
            icon="🔴",
            severity=severity,
            summary=summary,
            details={
                "cpu_percent": round(cpu, 1),
                "baseline_mean": round(cpu_stats.get("mean", 0), 1),
                "z_score": round(z, 2),
                "top_process": top_name,
                "top_process_cpu": round(top_cpu, 1),
            },
        )

    def _check_memory_pressure(
        self, snap: Dict, baseline: Dict, processes: List[Dict],
    ) -> BottleneckFinding:
        mem = snap.get("memory_percent", 0)
        swap = snap.get("swap_percent", 0)
        mem_stats = baseline.get("memory_percent", {"mean": 50, "std": 10})
        z = self._z_score(mem, mem_stats)

        # Top memory consumer
        mem_sorted = sorted(processes, key=lambda p: p.get("memory_percent", 0), reverse=True)
        top_proc = mem_sorted[0] if mem_sorted else {}
        top_mem = top_proc.get("memory_percent", 0)
        top_name = top_proc.get("name", "unknown")
        top_rss = top_proc.get("memory_rss", 0) / (1024 * 1024)  # MB

        severity = 0.0
        if mem > 80 and z > 1.0:
            severity = min(1.0, 0.3 + (z / 8))
        if swap > 20:
            severity = min(1.0, severity + 0.3)  # swap thrashing
        if mem > 92:
            severity = min(1.0, severity + 0.2)

        summary = ""
        if severity > 0:
            summary = (
                f"Memory at {mem:.0f}% ({z:.1f}σ above baseline), "
                f"swap at {swap:.0f}%. "
                f"Top consumer: '{top_name}' using {top_mem:.0f}% ({top_rss:.0f} MB RSS)."
            )

        return BottleneckFinding(
            category="Memory Pressure",
            icon="🟡",
            severity=severity,
            summary=summary,
            details={
                "memory_percent": round(mem, 1),
                "swap_percent": round(swap, 1),
                "baseline_mean": round(mem_stats.get("mean", 0), 1),
                "z_score": round(z, 2),
                "top_process": top_name,
                "top_process_mem_pct": round(top_mem, 1),
                "top_process_rss_mb": round(top_rss, 1),
            },
        )

    def _check_io_bottleneck(
        self, snap: Dict, baseline: Dict, processes: List[Dict],
    ) -> BottleneckFinding:
        disk_read = snap.get("disk_read_bytes", 0)
        disk_write = snap.get("disk_write_bytes", 0)
        read_stats = baseline.get("disk_read_bytes", {"mean": 0, "std": 1})
        write_stats = baseline.get("disk_write_bytes", {"mean": 0, "std": 1})

        z_read = self._z_score(disk_read, read_stats)
        z_write = self._z_score(disk_write, write_stats)
        z_max = max(z_read, z_write)

        disk_pct = snap.get("disk_percent", 0)

        severity = 0.0
        if z_max > 2.0:
            severity = min(1.0, 0.3 + (z_max / 10))
        if disk_pct > 90:
            severity = min(1.0, severity + 0.3)

        summary = ""
        if severity > 0:
            read_mb = disk_read / (1024 * 1024)
            write_mb = disk_write / (1024 * 1024)
            summary = (
                f"Disk I/O is {z_max:.1f}σ above baseline. "
                f"Read: {read_mb:.0f} MB, Write: {write_mb:.0f} MB. "
                f"Disk usage at {disk_pct:.0f}%."
            )

        return BottleneckFinding(
            category="I/O Bottleneck",
            icon="🟠",
            severity=severity,
            summary=summary,
            details={
                "disk_read_bytes": disk_read,
                "disk_write_bytes": disk_write,
                "disk_percent": round(disk_pct, 1),
                "z_read": round(z_read, 2),
                "z_write": round(z_write, 2),
            },
        )

    def _check_network(
        self, snap: Dict, baseline: Dict,
    ) -> BottleneckFinding:
        net_recv = snap.get("net_bytes_recv", 0)
        net_sent = snap.get("net_bytes_sent", 0)
        errors = snap.get("net_errin", 0) + snap.get("net_errout", 0)
        recv_stats = baseline.get("net_bytes_recv", {"mean": 0, "std": 1})

        z = self._z_score(net_recv, recv_stats)

        severity = 0.0
        if z > 2.5:
            severity = min(1.0, 0.3 + (z / 10))
        if errors > 0:
            severity = min(1.0, severity + 0.4)

        summary = ""
        if severity > 0:
            recv_mb = net_recv / (1024 * 1024)
            sent_mb = net_sent / (1024 * 1024)
            summary = (
                f"Network traffic is {z:.1f}σ above baseline. "
                f"Recv: {recv_mb:.0f} MB, Sent: {sent_mb:.0f} MB. "
                f"Errors: {errors:.0f}."
            )

        return BottleneckFinding(
            category="Network Saturation",
            icon="🔵",
            severity=severity,
            summary=summary,
            details={
                "net_bytes_recv": net_recv,
                "net_bytes_sent": net_sent,
                "net_errors": errors,
                "z_score": round(z, 2),
            },
        )

    def _check_thermal(self, snap: Dict) -> BottleneckFinding:
        temp = snap.get("cpu_temp_current")
        high = snap.get("cpu_temp_high", 90)
        throttled = snap.get("cpu_throttled", False)

        severity = 0.0
        if throttled:
            severity = 0.7
        if temp is not None and high and temp > high:
            severity = min(1.0, severity + 0.3)
        elif temp is not None and high and temp > high * 0.9:
            severity = max(severity, 0.3)

        summary = ""
        if severity > 0:
            freq = snap.get("cpu_freq_mhz", 0)
            summary = (
                f"CPU temperature at {temp:.0f}°C (threshold: {high:.0f}°C). "
                f"{'Throttling ACTIVE — frequency reduced.' if throttled else 'Approaching thermal limit.'} "
                f"Current frequency: {freq:.0f} MHz."
            )

        return BottleneckFinding(
            category="Thermal Throttle",
            icon="🌡️",
            severity=severity,
            summary=summary,
            details={
                "cpu_temp_current": temp,
                "cpu_temp_high": high,
                "cpu_throttled": throttled,
                "cpu_freq_mhz": snap.get("cpu_freq_mhz", 0),
            },
        )

    def _check_scheduler(self, snap: Dict) -> BottleneckFinding:
        load1 = snap.get("load_avg_1", 0)
        load5 = snap.get("load_avg_5", 0)
        cores = self.CPU_COUNT

        # Scheduler contention: load average significantly exceeds core count
        ratio = load1 / max(cores, 1)

        severity = 0.0
        if ratio > 1.5:
            severity = min(1.0, 0.3 + ((ratio - 1.5) / 5))
        if ratio > 3.0:
            severity = min(1.0, severity + 0.3)

        summary = ""
        if severity > 0:
            summary = (
                f"Load average ({load1:.1f}) is {ratio:.1f}x the CPU core count ({cores}). "
                f"Too many runnable threads competing for CPU time. "
                f"5-min load: {load5:.1f}."
            )

        return BottleneckFinding(
            category="Scheduler Contention",
            icon="🟣",
            severity=severity,
            summary=summary,
            details={
                "load_avg_1": round(load1, 2),
                "load_avg_5": round(load5, 2),
                "cpu_count": cores,
                "load_to_core_ratio": round(ratio, 2),
            },
        )

    # ──────────────────────────────────────────────────────────
    # Recommendation generator
    # ──────────────────────────────────────────────────────────

    def _generate_recommendation(
        self, primary: Optional[BottleneckFinding], processes: List[Dict],
    ) -> str:
        if primary is None:
            return (
                "No significant bottleneck detected. The system metrics during "
                "the anomaly window are within normal operating ranges. "
                "The anomaly may have been transient — continue monitoring."
            )

        cat = primary.category
        top_proc = processes[0].get("name", "unknown") if processes else "unknown"

        recommendations = {
            "CPU Bound": (
                f"The system is CPU-bound. Process '{top_proc}' is the primary contributor. "
                f"Actions: (1) Check if '{top_proc}' is performing a compilation or build task — "
                f"this is expected during software deployment. "
                f"(2) If unexpected, consider limiting CPU affinity or priority with 'nice'/'cpulimit'. "
                f"(3) If persistent, investigate the process for infinite loops or excessive computation."
            ),
            "Memory Pressure": (
                f"The system is under memory pressure. Process '{top_proc}' is consuming the most RAM. "
                f"Actions: (1) Check for memory leaks in '{top_proc}' using profiling tools. "
                f"(2) If this is a deployment, the new release may have higher memory requirements — "
                f"consider scaling the instance. "
                f"(3) Reduce swap thrashing by killing non-essential processes or adding RAM."
            ),
            "I/O Bottleneck": (
                f"Disk I/O is saturated, causing system-wide slowdowns. "
                f"Actions: (1) Identify which process is performing heavy reads/writes (likely '{top_proc}'). "
                f"(2) If deploying software, large file copies or database migrations are common causes. "
                f"(3) Consider using 'ionice' to deprioritize background I/O. "
                f"(4) Check if disk is nearing capacity (>90%)."
            ),
            "Network Saturation": (
                f"Network bandwidth is abnormally high. "
                f"Actions: (1) Check if a large download or upload is in progress (deployment artifacts). "
                f"(2) Monitor for packet errors which indicate hardware/configuration issues. "
                f"(3) If unexpected, investigate for potential data exfiltration."
            ),
            "Thermal Throttle": (
                f"The CPU is thermally throttling — reducing clock speed to prevent overheating. "
                f"Actions: (1) Check physical cooling (fans, airflow, thermal paste). "
                f"(2) Reduce concurrent workload to lower heat output. "
                f"(3) If in a VM or cloud, contact the provider about host thermal issues."
            ),
            "Scheduler Contention": (
                f"Too many threads/processes are competing for CPU time. "
                f"The load average far exceeds the available CPU cores. "
                f"Actions: (1) Identify and kill zombie or orphaned processes. "
                f"(2) Reduce parallelism in build tools (e.g., 'make -j2' instead of 'make -j16'). "
                f"(3) If deploying, stagger service restarts to avoid thundering herd."
            ),
        }

        return recommendations.get(cat, f"Investigate the '{cat}' bottleneck further.")
