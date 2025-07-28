
import asyncio
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

    # async def _fetch_one(self, station_id: str, date_str: str) -> Optional[List[Dict[str, Any]]]:
    async def _fetch_one(self, station_id: str) -> Optional[List[Dict[str, Any]]]:
        # Use the 'observations/hourly/7day' endpoint for hourly PWS data
        endpoint = "observations/hourly/7day"
        # params = {"stationId": station_id, "format": "json", "apiKey": self.api_key, "units": "m", "date": date_str}
        params = {"stationId": station_id, "format": "json", "apiKey": self.api_key, "units": "m"}
        data = await self._request("GET", endpoint, params=params)
        if data:
            return data.get('observations')
        return None

    async def fetch_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Fetches WU hourly data for a given date range using observations/hourly/7day endpoint."""
        if not self.api_key or not self.stations:
            log.error("Weather Underground API key or station list is not configured properly.")
            return pd.DataFrame()

        # despite the API claims, I believe it works beyond intended (can retrieve data past 7 days; as it did for rapid daily)
        # start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        # end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        # requests = [
        #     (s['stationId'], (start_dt + timedelta(days=d)).strftime("%Y%m%d"))
        #     for s in self.stations if 'stationId' in s
        #     for d in range((end_dt - start_dt).days + 1)
        # ]
        # tasks = [self._fetch_one(station_id, date) for station_id, date in requests]
        # The endpoint returns up to 7 days of hourly data per station, so we only need one call per station
        tasks = [self._fetch_one(s['stationId']) for s in self.stations if 'stationId' in s]

        all_obs = []
        for future in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Fetching WU Data"):
            result = await future
            if result:
                all_obs.extend(result)

        if not all_obs:
            return pd.DataFrame()

        processed_obs = []
        for obs in all_obs:
            if 'metric' in obs and obs['metric'] is not None:
                # Ensure 'metric' key exists and is not None before processing
                metric_data = obs.pop('metric')
                processed_obs.append({**obs, **metric_data})
        
        if not processed_obs:
            return pd.DataFrame()

        # Now safe to create the DataFrame
        df = pd.DataFrame(processed_obs)

        # Filter by the requested date range
        if 'obsTimeUtc' in df.columns:
            df['obsTimeUtc'] = pd.to_datetime(df['obsTimeUtc'])
            start_dt = pd.to_datetime(start_date)
            # Add one day to the end_date to make the range inclusive
            end_dt = pd.to_datetime(end_date) + pd.Timedelta(days=1)
            
            # Using '<' with the next day's start is a robust way to include the whole end day
            mask = (df['obsTimeUtc'] >= start_dt) & (df['obsTimeUtc'] < end_dt)
            df = df.loc[mask]
            
        return df
