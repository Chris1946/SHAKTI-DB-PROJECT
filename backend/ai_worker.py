"""
PulseTrace Backend — AI Anomaly Detection Engine (Worker)
=========================================================

A standalone background worker process that periodically queries
historical telemetry from ShaktiDB, runs an Isolation Forest
anomaly detection model from scikit-learn, and injects insights
directly into the Alerts table.

Architecture:
- Fetches the last `TRAINING_WINDOW_MINUTES` of data as a baseline.
- Trains an `IsolationForest` on the baseline.
- Runs inference on the last `INFERENCE_WINDOW_MINUTES` to find anomalies.
- If anomalies are detected, they are formatted as high-severity alerts.

Run independently via: `python ai_worker.py`
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Import database and models from the FastAPI backend
from app.database.connection import async_session_factory
from app.models.metrics import Alert, SystemMetric

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] AI_ENGINE: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ai_worker")

POLL_INTERVAL_SECONDS = 30
TRAINING_WINDOW_MINUTES = 60 * 24  # Train on last 24 hours
INFERENCE_WINDOW_MINUTES = 5       # Detect anomalies in the last 5 minutes
CONTAMINATION = 0.01               # Expect 1% of data to be anomalous

# ---------------------------------------------------------------------------
# AI Worker
# ---------------------------------------------------------------------------

class AIEngineWorker:
    def __init__(self) -> None:
        self.running = False
        self.model = IsolationForest(
            contamination=CONTAMINATION,
            random_state=42,
            n_jobs=-1, # use all cores
        )

    async def start(self) -> None:
        """Start the infinite polling loop."""
        self.running = True
        logger.info("AI Anomaly Engine started. Polling every %d seconds.", POLL_INTERVAL_SECONDS)
        
        while self.running:
            try:
                await self._run_cycle()
            except Exception as e:
                logger.error("Error in AI Engine cycle: %s", e, exc_info=True)
            
            # Sleep in small increments to allow for quick shutdown
            for _ in range(POLL_INTERVAL_SECONDS * 10):
                if not self.running:
                    break
                await asyncio.sleep(0.1)

    def stop(self) -> None:
        logger.info("Stopping AI Engine...")
        self.running = False

    async def _run_cycle(self) -> None:
        """One complete cycle of fetch -> train -> infer -> alert."""
        now = datetime.now(timezone.utc)
        train_since = now - timedelta(minutes=TRAINING_WINDOW_MINUTES)
        
        async with async_session_factory() as session:
            # 1. Fetch data
            logger.info("Fetching data for AI engine...")
            
            # Fetch SystemMetrics
            query = (
                select(SystemMetric)
                .where(SystemMetric.collected_at >= train_since)
                .order_by(SystemMetric.collected_at.asc())
            )
            result = await session.execute(query)
            metrics = result.scalars().all()
            
            if not metrics:
                logger.warning("No metrics found in the last %d minutes.", TRAINING_WINDOW_MINUTES)
                return
                
            # 2. Preprocess Data
            # Convert to DataFrame
            data_dicts = []
            for m in metrics:
                data_dicts.append({
                    "id": m.id,
                    "hostname": m.hostname,
                    "collected_at": m.collected_at,
                    "cpu_percent": float(m.cpu_percent) if m.cpu_percent is not None else 0.0,
                    "memory_percent": float(m.memory_percent) if m.memory_percent is not None else 0.0,
                    "disk_percent": float(m.disk_percent) if m.disk_percent is not None else 0.0,
                })
                
            df = pd.DataFrame(data_dicts)
            if df.empty:
                return
                
            # Features for anomaly detection
            features = ["cpu_percent", "memory_percent", "disk_percent"]
            X = df[features].fillna(0)
            
            # 3. Train / Predict
            # Fit the model on the full window (baseline)
            logger.info("Training IsolationForest on %d records...", len(df))
            self.model.fit(X)
            
            # Predict
            df["anomaly"] = self.model.predict(X)
            df["anomaly_score"] = self.model.decision_function(X)
            
            # Filter to anomalies (-1) in the INFERENCE window
            infer_since = now - timedelta(minutes=INFERENCE_WINDOW_MINUTES)
            recent_anomalies = df[
                (df["anomaly"] == -1) & 
                (df["collected_at"] >= infer_since)
            ]
            
            if recent_anomalies.empty:
                logger.debug("No anomalies detected in the last %d minutes.", INFERENCE_WINDOW_MINUTES)
                return
                
            # 4. Generate Alerts
            # Group by hostname to avoid spamming
            logger.warning("Detected %d anomalous data points!", len(recent_anomalies))
            
            # Deduplication window for AI alerts (e.g. 15 minutes)
            dedup_window = now - timedelta(minutes=15)
            alerts_created = 0
            
            for hostname, group in recent_anomalies.groupby("hostname"):
                # Find the worst anomaly score in the group (most negative)
                worst_idx = group["anomaly_score"].idxmin()
                worst_row = group.loc[worst_idx]
                
                # Check for existing recent unresolved AI alert for this host
                existing_query = (
                    select(Alert.id)
                    .where(Alert.hostname == hostname)
                    .where(Alert.source == "ai_engine")
                    .where(Alert.resolved == False)
                    .where(Alert.created_at >= dedup_window)
                    .limit(1)
                )
                existing = await session.execute(existing_query)
                if existing.scalar() is not None:
                    continue # Skip, already alerted recently
                    
                # Create the Alert
                # Identify which feature contributed most to the anomaly (heuristic: which is highest relative to its mean)
                # For a better approach, one would use SHAP values, but simple max deviation works here.
                means = X.mean()
                deviations = (worst_row[features] - means) / (X.std() + 1e-9)
                top_feature = deviations.idxmax()
                top_val = worst_row[top_feature]
                
                alert_msg = (
                    f"AI Anomaly Detected: Abnormal system behavior. "
                    f"Key contributor: {top_feature} at {top_val:.1f}%. "
                    f"(Score: {worst_row['anomaly_score']:.3f})"
                )
                
                alert = Alert(
                    hostname=hostname,
                    severity="warning", # AI anomalies are typically warnings unless tied to a hard failure
                    category="ai_anomaly",
                    message=alert_msg,
                    metric_value=float(top_val),
                    threshold=None,
                    source="ai_engine",
                )
                
                session.add(alert)
                alerts_created += 1
                
            if alerts_created > 0:
                await session.commit()
                logger.info("Generated %d AI alerts.", alerts_created)



# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

async def main() -> None:
    worker = AIEngineWorker()

    def handle_sigint(sig: int, frame: Any) -> None:
        worker.stop()

    signal.signal(signal.SIGINT, handle_sigint)
    signal.signal(signal.SIGTERM, handle_sigint)

    await worker.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    finally:
        logger.info("AI Engine fully stopped.")
