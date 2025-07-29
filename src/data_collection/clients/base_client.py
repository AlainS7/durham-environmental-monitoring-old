import asyncio
import httpx
import logging
import pandas as pd
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

log = logging.getLogger(__name__)

class BaseClient(ABC):
    """Abstract base class for API clients."""

    def __init__(self, base_url: str, api_key: Optional[str] = None, semaphore_limit: int = 10):
        self.base_url = base_url
        self.api_key = api_key
        self.semaphore = asyncio.Semaphore(semaphore_limit)
        self.client = httpx.AsyncClient()  # Reuse a single client instance

    async def aclose(self):
        """Close the underlying HTTP client session."""
        await self.client.aclose()

    async def _request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None,
                       headers: Optional[Dict[str, str]] = None, json_data: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """Makes an asynchronous HTTP request."""
        async with self.semaphore:
            try:
                response = await self.client.request(
                    method, f"{self.base_url}/{endpoint}",
                    params=params,
                    headers=headers,
                    json=json_data,
                    timeout=60.0
                )
                response.raise_for_status()
                if response.status_code == 204:
                    return None
                return response.json()
            except httpx.HTTPStatusError as e:
                log.warning(f"API request to {e.request.url} failed with status {e.response.status_code}: {e.response.text}")
            except Exception as e:
                log.error(f"API request failed: {e}", exc_info=True)
            return None

    @abstractmethod
    async def fetch_data(self, **kwargs) -> pd.DataFrame:
        """Fetches data from the API and returns it as a DataFrame."""
        pass