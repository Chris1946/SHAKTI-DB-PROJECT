import os
import sys
import subprocess
import urllib.request
import urllib.error
import time
import logging
from PySide6.QtCore import QThread, Signal

logger = logging.getLogger("pulsetrace.desktop.bootstrapper")

class BootstrapperThread(QThread):
    """
    Background thread that ensures the backend and agent are running.
    If the backend is not reachable, it assumes it needs to start it using docker-compose.
    It then starts the agent logic natively in a background thread.
    """
    status_update = Signal(str)
    finished_bootstrap = Signal(bool)

    def __init__(self):
        super().__init__()
        self._is_running = True
        self.agent_thread = None

    def get_base_path(self):
        """Get the base path where docker-compose.yml and agent/ are located."""
        if getattr(sys, 'frozen', False):
            # PyInstaller bundle
            return sys._MEIPASS
        # Running from source
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def is_backend_alive(self):
        try:
            req = urllib.request.urlopen("http://localhost:8000/api/v1/health", timeout=2)
            return req.getcode() == 200
        except Exception:
            return False

    def start_docker(self):
        base_path = self.get_base_path()
        docker_compose_path = os.path.join(base_path, "docker-compose.yml")
        
        if not os.path.exists(docker_compose_path):
            logger.error(f"docker-compose.yml not found at {docker_compose_path}")
            return False

        self.status_update.emit("Starting Docker containers...")
        try:
            # We don't want to block the UI completely if docker takes a while,
            # but we are in a QThread, so subprocess.run is fine.
            # Using Popen to capture output if needed, but run is simpler.
            env = os.environ.copy()
            subprocess.run(
                ["docker", "compose", "up", "-d"],
                cwd=base_path,
                env=env,
                check=True,
                capture_output=True
            )
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to start Docker: {e.stderr.decode()}")
            return False
        except FileNotFoundError:
            logger.error("Docker is not installed or not in PATH.")
            return False

    def start_agent_natively(self):
        """Run the agent logic natively inside this process."""
        self.status_update.emit("Starting background agent...")
        base_path = self.get_base_path()
        agent_path = os.path.join(base_path, "agent")
        
        if agent_path not in sys.path:
            sys.path.insert(0, agent_path)

        try:
            # Import agent main dynamically so it uses the updated sys.path
            import asyncio
            from agent.main import main as agent_main
            
            # Run the agent's asyncio loop forever
            logger.info("Starting integrated Agent loop...")
            asyncio.run(agent_main())
        except Exception as e:
            logger.error(f"Failed to run agent natively: {e}", exc_info=True)

    def run(self):
        # 1. Check if we need to start Docker
        if not self.is_backend_alive():
            self.status_update.emit("Backend offline. Bootstrapping...")
            success = self.start_docker()
            if success:
                # Wait for backend to actually become healthy
                self.status_update.emit("Waiting for backend to initialize...")
                retries = 0
                while retries < 30 and not self.is_backend_alive():
                    time.sleep(1)
                    retries += 1
            else:
                self.status_update.emit("Failed to bootstrap backend.")
                self.finished_bootstrap.emit(False)
                return

        self.status_update.emit("Backend is online!")
        self.finished_bootstrap.emit(True)

        # 2. Start the Agent in this thread (blocks forever)
        # We do this after emitting finished_bootstrap so the UI can load.
        self.start_agent_natively()

    def stop(self):
        self._is_running = False
        # The agent natively handles SIGINT, but since it's in a QThread,
        # we might just let it die when the process exits.
