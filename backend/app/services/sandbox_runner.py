import os
import subprocess
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class SandboxRunner:
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.process = None

    def execute(self) -> Dict[str, Any]:
        """
        Executes the project in a sandboxed environment.
        For this MVP, it runs as a subprocess locally.
        In a production environment, this would spin up a Docker container.
        """
        if not os.path.exists(self.project_path):
            raise FileNotFoundError(f"Project path not found: {self.project_path}")
            
        logger.info(f"Preparing to sandbox execute: {self.project_path}")
        
        # Simple heuristic to find an entry point (e.g., main.py, app.py, index.js)
        entry_point = self._find_entry_point()
        if not entry_point:
            return {"status": "error", "message": "No valid entry point found (e.g., main.py, app.py)"}
            
        command = self._build_execution_command(entry_point)
        
        try:
            # We run it in the background using Popen
            logger.info(f"Executing: {' '.join(command)}")
            self.process = subprocess.Popen(
                command, 
                cwd=self.project_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            return {
                "status": "success", 
                "pid": self.process.pid, 
                "entry_point": entry_point,
                "message": "Execution started in sandbox."
            }
            
        except Exception as e:
            logger.error(f"Failed to execute sandbox: {e}")
            return {"status": "error", "message": str(e)}

    def _find_entry_point(self) -> str:
        common_entry_points = ["main.py", "app.py", "index.py", "server.py", "manage.py", "index.js", "app.js"]
        for entry in common_entry_points:
            if os.path.exists(os.path.join(self.project_path, entry)):
                return entry
        return None
        
    def _build_execution_command(self, entry_point: str) -> list:
        if entry_point.endswith(".py"):
            return ["python", entry_point]
        elif entry_point.endswith(".js"):
            return ["node", entry_point]
        else:
            return ["./" + entry_point]

    def stop(self):
        """Stops the running sandbox."""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            logger.info(f"Terminated sandbox process {self.process.pid}")
