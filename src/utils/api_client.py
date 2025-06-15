"""
Enhanced API client with rate limiting and retry logic
"""
import time
import asyncio
from typing import Optional, Dict, Any
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

class APIClient:
    """Enhanced API client with rate limiting and retry logic"""
    
    def __init__(self, base_url: str, rate_limit_per_second: float = 1.0):
        self.base_url = base_url
        self.rate_limit = rate_limit_per_second
        self.last_request_time = 0
        self.session = httpx.AsyncClient(timeout=30.0)
    
    async def _rate_limit(self):
        """Implement rate limiting"""
        now = time.time()
        time_since_last = now - self.last_request_time
        min_interval = 1.0 / self.rate_limit
        
        if time_since_last < min_interval:
            await asyncio.sleep(min_interval - time_since_last)
        
        self.last_request_time = time.time()
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[Any, Any]:
        """Make GET request with retry logic"""
        await self._rate_limit()
        
        url = f"{self.base_url}/{endpoint}"
        response = await self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.aclose()

# Usage example:
# async with APIClient("https://api.tsi.com", rate_limit_per_second=0.5) as client:
#     data = await client.get("telemetry", {"device_id": "123"})
