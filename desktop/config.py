import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from the root .env file if it exists
root_dir = Path(__file__).resolve().parent.parent
env_path = root_dir / ".env"
load_dotenv(env_path)

class Config:
    """Desktop Application Configuration"""
    
    # API Configuration
    API_BASE_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1")
    API_KEY = os.getenv("API_KEY", "")
    
    # Polling configuration
    POLL_INTERVAL_MS = int(os.getenv("DESKTOP_POLL_INTERVAL_MS", "5000"))
    
    # UI Configuration
    WINDOW_TITLE = "PulseTrace - eBPF Systems Monitor"
    WINDOW_WIDTH = 1280
    WINDOW_HEIGHT = 800
    
    # Request Timeouts
    TIMEOUT_SEC = 120.0

config = Config()
