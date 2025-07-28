
import asyncio
import pandas as pd
import logging
from tqdm import tqdm
from typing import Optional

from .base_client import BaseClient
from src.utils.config_loader import get_wu_stations

log = logging.getLogger(__name__)

class WUClient(BaseClient):
    """Client for fetching data from the Weather Underground API."""

    def __init__(self, api_key: str, base_url: str = "https://api.weather.com/v2/pws"):
        super().__init__(base_url, api_key)
        self.stations = get_wu_stations()

    async def _fetch_one(self, station_id: str, date_str: str) -> Optional[pd.DataFrame]:
        """Fetches all rapid observations for a single station and day, returns as DataFrame."""
        endpoint = "observations/all/1day"
        params = {
            "stationId": station_id,
            "format": "json",
            "apiKey": self.api_key,
            "units": "m"
        }
        # The endpoint returns all obs for the given day; date_str is YYYY-MM-DD
        # We'll filter locally after fetching
        data = await self._request("GET", endpoint, params=params)
        if data and 'observations' in data:
            obs = data['observations']
            processed = []
            for o in obs:
                # Flatten the 'metric' dict into the main record
                metric = o.pop('metric', {}) if 'metric' in o and o['metric'] is not None else {}
                processed.append({**o, **metric})
            if processed:
                df = pd.DataFrame(processed)
                df['stationID'] = station_id
                # Filter to just the requested date
                if 'obsTimeUtc' in df.columns:
                    df['obsTimeUtc'] = pd.to_datetime(df['obsTimeUtc'])
                    date_start = pd.to_datetime(date_str).tz_localize('UTC')
                    date_end = date_start + pd.Timedelta(days=1)
                    mask = (df['obsTimeUtc'] >= date_start) & (df['obsTimeUtc'] < date_end)
                    df = df.loc[mask]
                return df
        return None

    async def fetch_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetches WU rapid (5-min) data for a given date range, aggregates to hourly summaries.
        """
        if not self.api_key or not self.stations:
            log.error("Weather Underground API key or station list is not configured properly.")
            return pd.DataFrame()

        log.info("Building list of requests for all stations and dates...")
        date_range = pd.date_range(start=start_date, end=end_date)
        requests = [
            (s['stationId'], d.strftime("%Y-%m-%d"))
            for s in self.stations if 'stationId' in s
            for d in date_range
        ]
        tasks = [self._fetch_one(station_id, date_str) for station_id, date_str in requests]

        log.info(f"Starting async fetch for {len(tasks)} station-date combinations...")
        all_results = []
        for future in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Fetching WU Data"):
            result = await future
            if result is not None and not result.empty:
                all_results.append(result)

        log.info(f"Fetched data for {len(all_results)} station-date combinations.")

        if not all_results:
            log.warning("No data fetched from WU API.")
            return pd.DataFrame()

        log.info("Concatenating all results into a single DataFrame...")
        raw_df = pd.concat(all_results, ignore_index=True)
        if raw_df.empty or 'obsTimeUtc' not in raw_df.columns:
            log.warning("No valid data after concatenation.")
            return pd.DataFrame()

        log.info("Converting obsTimeUtc to datetime and setting as index...")
        raw_df['obsTimeUtc'] = pd.to_datetime(raw_df['obsTimeUtc'])
        raw_df.set_index('obsTimeUtc', inplace=True)

        log.info("Preparing aggregation dictionary for hourly resampling...")
        numeric_cols = raw_df.select_dtypes(include='number').columns.tolist()
        # Exclude columns that should not be aggregated
        exclude_cols = ['epoch', 'lat', 'lon', 'qcStatus']
        agg_cols = [col for col in numeric_cols if col not in exclude_cols]
        agg_dict = {col: 'mean' for col in agg_cols}

        log.info("Starting groupby and hourly resampling...")
        final_df = raw_df.groupby('stationID').resample('h').agg(agg_dict)  # type: ignore

        log.info("Resetting index after resampling...")
        final_df = final_df.reset_index()

        log.info(f"Successfully resampled WU data to {len(final_df)} hourly records.")
        return final_df
