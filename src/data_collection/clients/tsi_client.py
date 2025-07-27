
import asyncio
import httpx
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from .base_client import BaseClient
from src.utils.config_loader import get_tsi_devices

log = logging.getLogger(__name__)

class TSIClient(BaseClient):
    """Client for fetching data from the TSI API."""

    def __init__(self, client_id: str, client_secret: str, auth_url: str, base_url: str = "https://api-prd.tsilink.com/api/v3/external"):
        super().__init__(base_url, semaphore_limit=3)
        self.client_id = client_id
        self.client_secret = client_secret
        self.auth_url = auth_url
        self.device_ids = get_tsi_devices()
        self.headers: Optional[Dict[str, str]] = None

    async def _authenticate(self) -> bool:
        """Authenticates with the TSI API to get an access token."""
        auth_data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        try:
            async with httpx.AsyncClient() as client:
                auth_resp = await client.post(self.auth_url, json=auth_data)
                auth_resp.raise_for_status()
                self.headers = {"Authorization": f"Bearer {auth_resp.json()['access_token']}", "Accept": "application/json"}
                return True
        except Exception as e:
            log.error(f"Failed to authenticate with TSI API: {e}", exc_info=True)
            return False

    async def _fetch_one_day(self, device_id: str, date_iso: str) -> Optional[pd.DataFrame]:
        """Fetches data for a single device and day."""
        if not self.headers:
            log.error("TSI client is not authenticated.")
            return None

        start_iso = f"{date_iso}T00:00:00Z"
        end_iso = (datetime.strptime(date_iso, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
        params = {'device_id': device_id, 'start_date': start_iso, 'end_date': end_iso}

        records = await self._request("GET", "telemetry", params=params, headers=self.headers)
        if records:
            df = pd.DataFrame(records)
            df['device_id'] = device_id
            return df
        return None

    async def fetch_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Fetches TSI data for a given date range."""
        if not await self._authenticate():
            return pd.DataFrame()

        date_range = pd.date_range(start=start_date, end=end_date)
        tasks = [self._fetch_one_day(dev_id, d.strftime("%Y-%m-%d"))
                 for dev_id in self.device_ids
                 for d in date_range]

        all_results = await asyncio.gather(*tasks)
        valid_dfs = [df for df in all_results if df is not None and not df.empty]
        return pd.concat(valid_dfs, ignore_index=True) if valid_dfs else pd.DataFrame()
