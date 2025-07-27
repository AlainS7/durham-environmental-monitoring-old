
import asyncio
import httpx
import pandas as pd
import logging
from datetime import datetime, timedelta
from tqdm import tqdm
from typing import List, Dict, Any, Optional

from .base_client import BaseClient
from src.utils.config_loader import get_wu_stations

log = logging.getLogger(__name__)

class WUClient(BaseClient):
    """Client for fetching data from the Weather Underground API."""

    def __init__(self, api_key: str, base_url: str = "https://api.weather.com/v2/pws"):
        super().__init__(base_url, api_key)
        self.stations = get_wu_stations()

    async def _fetch_one(self, station_id: str, date_str: Optional[str], is_backfill: bool) -> Optional[List[Dict[str, Any]]]:
        endpoint = "history/all" if is_backfill else "observations/all/1day"
        params = {"stationId": station_id, "format": "json", "apiKey": self.api_key, "units": "m"}
        if is_backfill and date_str:
            params["date"] = date_str

        data = await self._request("GET", endpoint, params=params)
        return data.get('observations') if data else None

    async def fetch_data(self, start_date: str, end_date: str, is_backfill: bool = False) -> pd.DataFrame:
        """Fetches WU data for a given date range."""
        if not self.api_key or not self.stations:
            log.error("Weather Underground API key or station list is not configured properly.")
            return pd.DataFrame()

        if is_backfill:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            requests = [(s['stationId'], (start_dt + timedelta(days=d)).strftime("%Y%m%d"))
                        for s in self.stations if 'stationId' in s
                        for d in range((end_dt - start_dt).days + 1)]
            tasks = [self._fetch_one(station_id, date, is_backfill) for station_id, date in requests]
        else:
            tasks = [self._fetch_one(s['stationId'], None, is_backfill) for s in self.stations if 'stationId' in s]

        all_obs = []
        for future in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Fetching WU Data"):
            result = await future
            if result:
                all_obs.extend(result)

        if not all_obs:
            return pd.DataFrame()

        flat_obs = [obs.update(obs.pop('metric')) or obs for obs in all_obs if 'metric' in obs]
        return pd.DataFrame(flat_obs or all_obs)
