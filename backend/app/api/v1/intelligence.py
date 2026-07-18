from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import logging
from app.services.static_analyzer import StaticAnalyzer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/intelligence", tags=["intelligence"])

class AnalyzeRequest(BaseModel):
    project_path: str

@router.post("/analyze")
async def analyze_project(request: AnalyzeRequest):
    """
    Triggers Stage 1: Static Code Intelligence on the given path.
    """
    if not os.path.exists(request.project_path):
        raise HTTPException(status_code=404, detail="Project path not found")
        
    try:
        analyzer = StaticAnalyzer(request.project_path)
        graph = analyzer.analyze()
        return {"status": "success", "graph": graph}
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class ExecuteRequest(BaseModel):
    project_path: str

# Keep track of active runners (in memory for MVP)
active_runners = {}

@router.post("/execute")
async def execute_project(request: ExecuteRequest):
    """
    Triggers Stage 2: Secure Execution on the given path.
    """
    from app.services.sandbox_runner import SandboxRunner
    
    if not os.path.exists(request.project_path):
        raise HTTPException(status_code=404, detail="Project path not found")
        
    try:
        runner = SandboxRunner(request.project_path)
        result = runner.execute()
        
        if result["status"] == "success":
            active_runners[request.project_path] = runner
            
        return result
    except Exception as e:
        logger.error(f"Execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
@router.post("/stop")
async def stop_project(request: ExecuteRequest):
    if request.project_path in active_runners:
        runner = active_runners[request.project_path]
        runner.stop()
        del active_runners[request.project_path]
        return {"status": "success", "message": "Sandbox stopped."}
    return {"status": "not_running", "message": "No active sandbox found for this path."}

import psutil
import time

_telemetry_cache = {}

@router.get("/telemetry/{pid}")
async def get_telemetry(pid: int):
    """
    Fetches real-time authentic telemetry for a given process using psutil.
    """
    try:
        proc = psutil.Process(pid)
        
        cpu_percent = proc.cpu_percent()
        mem_info = proc.memory_info()
        
        try:
            io = proc.io_counters()
            disk_read = io.read_bytes
            disk_write = io.write_bytes
        except (psutil.AccessDenied, AttributeError):
            disk_read = 0
            disk_write = 0
            
        connections = []
        try:
            for conn in proc.connections(kind='all'):
                if conn.raddr:
                    connections.append({
                        "remote_ip": conn.raddr.ip,
                        "remote_port": conn.raddr.port,
                        "status": conn.status
                    })
        except psutil.AccessDenied:
            pass
            
        now = time.time()
        rates = {"disk_read_rate": 0.0, "disk_write_rate": 0.0}
        
        if pid in _telemetry_cache:
            last_data = _telemetry_cache[pid]
            dt = now - last_data["time"]
            if dt > 0:
                rates["disk_read_rate"] = max(0, disk_read - last_data["disk_read"]) / dt
                rates["disk_write_rate"] = max(0, disk_write - last_data["disk_write"]) / dt
                
        _telemetry_cache[pid] = {
            "time": now,
            "disk_read": disk_read,
            "disk_write": disk_write
        }
        
        return {
            "status": "success",
            "cpu_percent": cpu_percent,
            "memory_rss": mem_info.rss if mem_info else 0,
            "disk_read_rate": rates["disk_read_rate"],
            "disk_write_rate": rates["disk_write_rate"],
            "connections": connections
        }
    except psutil.NoSuchProcess:
        raise HTTPException(status_code=404, detail="Process not found or exited")
    except Exception as e:
        logger.error(f"Telemetry failed for pid {pid}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
