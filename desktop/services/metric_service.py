from typing import List, Dict, Any
from desktop.services.api_client import APIClient

class MetricService:
    """
    Service layer for querying metrics and alerts from the backend.
    Translates raw JSON responses into domain objects or dictionaries for the UI.
    """
    
    def __init__(self):
        self.api = APIClient()

    def get_latest_system_metrics(self) -> List[Dict[str, Any]]:
        """
        Fetch the most recent system metrics for all hosts.
        """
        data = self.api.get("/metrics/latest")
        if not isinstance(data, list):
            return []
        # Sanitize metrics
        for item in data:
            item["cpu_percent"] = max(0.0, min(100.0, float(item.get("cpu_percent", 0.0))))
            item["memory_percent"] = max(0.0, min(100.0, float(item.get("memory_percent", 0.0))))
        return data
        
    def get_historical_metrics(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """
        Fetch historical system metrics for charting.
        """
        data = self.api.get("/metrics", params={"minutes": minutes})
        return data if isinstance(data, list) else []

    def get_latest_processes(self, limit: int = 25) -> List[Dict[str, Any]]:
        """
        Fetch the most recent process snapshot, sorted by CPU % descending.
        """
        data = self.api.get("/processes/latest", params={"limit": limit})
        return data if isinstance(data, list) else []

    def get_alerts(self) -> List[Dict[str, Any]]:
        """
        Fetch active or recent alerts.
        """
        return self.api.get("/alerts")

    def resolve_alert(self, alert_id: int) -> Dict[str, Any]:
        """
        Mark an alert as resolved via PATCH /alerts/{id}/resolve.
        """
        return self.api.patch(f"/alerts/{alert_id}/resolve")

    def analyze_alert(self, alert_id: int) -> Dict[str, Any]:
        """
        Trigger AI Root Cause Analysis for a specific alert.
        """
        return self.api.post(f"/ai/alerts/{alert_id}/analyze")
