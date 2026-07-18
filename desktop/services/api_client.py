import logging
import requests
from typing import Any, Dict, Optional

from desktop.config import config

logger = logging.getLogger(__name__)

class APIClientError(Exception):
    """Base exception for API client errors."""
    pass

class APIClient:
    """
    HTTP client for communicating with the FastAPI backend.
    Handles authentication, error wrapping, and timeouts.
    """
    
    def __init__(self):
        self.base_url = config.API_BASE_URL.rstrip('/')
        self.session = requests.Session()
        
        # Inject the API key if configured
        if config.API_KEY:
            self.session.headers.update({"X-API-Key": config.API_KEY})
        self.session.headers.update({"Content-Type": "application/json"})

    def _request(self, method: str, endpoint: str, params: Optional[Dict] = None, json: Optional[Dict] = None) -> Any:
        """
        Internal method to execute HTTP requests with error handling.
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json,
                timeout=config.TIMEOUT_SEC
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error: {e.response.status_code} on {url}")
            raise APIClientError(f"HTTP Error: {e.response.status_code}") from e
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection Error to {url}")
            raise APIClientError("Failed to connect to the backend server.") from e
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout connecting to {url}")
            raise APIClientError("Request to backend timed out.") from e
        except Exception as e:
            logger.error(f"Unexpected error calling {url}: {str(e)}")
            raise APIClientError(f"Unexpected error: {str(e)}") from e

    def get(self, endpoint: str, params: Optional[Dict] = None) -> Any:
        """Execute a GET request."""
        return self._request("GET", endpoint, params)

    def post(self, endpoint: str, json: Optional[Dict] = None) -> Any:
        """Execute a POST request."""
        return self._request("POST", endpoint, json=json)

    def patch(self, endpoint: str, json: Optional[Dict] = None) -> Any:
        """Execute a PATCH request."""
        return self._request("PATCH", endpoint, json=json)
