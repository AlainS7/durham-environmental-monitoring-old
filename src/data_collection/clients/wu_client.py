

import asyncio
import pandas as pd
import logging
from tqdm import tqdm
from typing import Optional
import pydantic

from .base_client import BaseClient
from src.utils.config_loader import get_wu_stations
from src.data_collection.models import WUResponse

log = logging.getLogger(__name__)

class WUClient(BaseClient):
    """Client for fetching data from the Weather Underground API."""

    # FEAT: change use_all_endpoint bool as needed (below or --use-all-endpoint)
    def __init__(self, api_key: str, base_url: str = "https://api.weather.com/v2/pws", use_all_endpoint: bool = False, force_1day_multiday_mode: bool = False, use_history_hourly_endpoint: bool = True):
        """
        use_all_endpoint: If True, use 'observations/all' (multi-day, no date param), else 'observations/all/1day' (per-day).
        force_1day_multiday_mode: If True and use_all_endpoint is False, loop over date range and fetch each day with /1day endpoint.
        use_history_hourly_endpoint: If True, use 'history/hourly' endpoint (per-day, per-station, most reliable for old data).
        """
        super().__init__(base_url, api_key)
        self.stations = get_wu_stations()
        self.use_all_endpoint = use_all_endpoint
        self.force_1day_multiday_mode = force_1day_multiday_mode
        self.use_history_hourly_endpoint = use_history_hourly_endpoint

    async def _fetch_one(self, station_id: str, start_date: str, end_date: str = "") -> Optional[pd.DataFrame]:
        """
        Fetches all rapid observations for a single station and date range, returns as DataFrame.
        If using /all endpoint, fetches all data for the range in one call; else, expects start_date == end_date and fetches for that day.
        If using /history/hourly endpoint, fetches hourly summary for a single day and station.
        Uses Pydantic WUResponse for validation.
        """
        data = None
        filter_end_date_for_helper = "" # Initialize for clarity
        if self.use_history_hourly_endpoint:
            # Use /history/hourly endpoint (per-day, per-station)
            endpoint = "history/hourly"
            date_param = start_date.replace("-", "") # The date param for this endpoint is YYYYMMDD
            params = {
                "stationId": station_id,
                "date": date_param,
                "format": "json",
                "apiKey": self.api_key,
                "units": "m",
                "numericPrecision": "decimal"
            }
            data = await self._request("GET", endpoint, params=params)
            filter_end_date_for_helper = start_date # For history/hourly, filter for just the start_date
        elif self.use_all_endpoint:
            endpoint = "observations/all"
            filter_end_date_for_helper = end_date if end_date else start_date # Use the actual end_date for filtering
            params = {
                "stationId": station_id,
                "format": "json",
                "apiKey": self.api_key,
                "units": "m",
                "startDate": start_date,  # YYYY-MM-DD
                "endDate": filter_end_date_for_helper  # YYYY-MM-DD
            }
            data = await self._request("GET", endpoint, params=params)
        else:
            endpoint = "observations/all/1day"
            filter_end_date_for_helper = start_date # For 1day endpoint, filter for just the start_date
            params = {
                "stationId": station_id,
                "format": "json",
                "apiKey": self.api_key,
                "units": "m"
            }
            data = await self._request("GET", endpoint, params=params)

        # Validate and parse using Pydantic WUResponse
        try:
            validated = WUResponse.model_validate(data)
        except pydantic.ValidationError as e:
            log.error(f"WU API response validation failed for station {station_id}: {e}")
            return None

        # Convert validated observations to dicts for DataFrame
        obs_dicts = [obs.model_dump() for obs in validated.observations]
        # The 'imperial' block is redundant since we requested metric units.
        # We will only use the top-level metric values.
        for o in obs_dicts:
            o.pop('imperial', None) # Safely remove the imperial block

        if obs_dicts:
            df = pd.DataFrame(obs_dicts)
            log.debug(f"Raw DataFrame shape for station {station_id}: {df.shape}")
            df['stationID'] = station_id
            # Filter to just the requested date range
            if 'obsTimeUtc' in df.columns:
                df['obsTimeUtc'] = pd.to_datetime(df['obsTimeUtc'])
                date_start_utc = pd.to_datetime(start_date).tz_localize('UTC')
                # The filter_end_date is inclusive, so we add one day for the exclusive upper bound
                date_end_utc = pd.to_datetime(filter_end_date_for_helper).tz_localize('UTC') + pd.Timedelta(days=1)
                mask = (df['obsTimeUtc'] >= date_start_utc) & (df['obsTimeUtc'] < date_end_utc)
                df = df.loc[mask]
                log.debug(f"Filtered DataFrame shape for station {station_id} from {start_date} to {filter_end_date_for_helper}: {df.shape}")
            return df
        return None

    # _process_and_filter_observations is no longer needed; validation and flattening are handled in _fetch_one

    async def fetch_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetches WU rapid (5-min) data for a given date range, aggregates to hourly summaries.
        If use_all_endpoint is True, fetches all data for each station in one call.
        If use_all_endpoint is False and force_1day_multiday_mode is True, loops over date range and fetches each day with /1day endpoint.
        Otherwise, fetches per day per station (default behavior).
        If use_history_hourly_endpoint is True, uses /history/hourly endpoint (per-day, per-station, most reliable for old data).
        """
        if not self.api_key or not self.stations:
            log.error("Weather Underground API key or station list is not configured properly.")
            return pd.DataFrame()

        all_results = []
        if self.use_history_hourly_endpoint:
            log.info("Building list of requests for all stations and all days in range using /history/hourly endpoint...")
            date_range = pd.date_range(start=start_date, end=end_date)
            for s in self.stations:
                if 'stationId' not in s:
                    continue
                station_id = s['stationId']
                station_results = []
                for d in date_range:
                    date_str = d.strftime("%Y-%m-%d")
                    result = await self._fetch_one(station_id, date_str)
                    if result is not None and not result.empty:
                        station_results.append(result)
                if station_results:
                    all_results.append(pd.concat(station_results, ignore_index=True))
            log.info(f"Fetched data for {len(all_results)} stations (multiday /history/hourly mode).")
        elif self.use_all_endpoint:
            log.info("Building list of requests for all stations (one call per station for full date range)...")
            tasks = [self._fetch_one(s['stationId'], start_date, end_date)
                     for s in self.stations if 'stationId' in s]
            log.info(f"Starting async fetch for {len(tasks)} stations...")
            for future in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Fetching WU Data"):
                result = await future
                if result is not None and not result.empty:
                    all_results.append(result)
            log.info(f"Fetched data for {len(all_results)} stations.")
        elif self.force_1day_multiday_mode:
            log.info("Building list of requests for all stations and all days in range using /1day endpoint...")
            date_range = pd.date_range(start=start_date, end=end_date)
            for s in self.stations:
                if 'stationId' not in s:
                    continue
                station_id = s['stationId']
                station_results = []
                for d in date_range:
                    date_str = d.strftime("%Y-%m-%d")
                    result = await self._fetch_one(station_id, date_str)
                    if result is not None and not result.empty:
                        station_results.append(result)
                if station_results:
                    all_results.append(pd.concat(station_results, ignore_index=True))
            log.info(f"Fetched data for {len(all_results)} stations (multiday /1day mode).")
        else:
            log.info("Building list of requests for all stations and dates...")
            date_range = pd.date_range(start=start_date, end=end_date)
            requests = [
                (s['stationId'], d.strftime("%Y-%m-%d"))
                for s in self.stations if 'stationId' in s
                for d in date_range
            ]
            tasks = [self._fetch_one(station_id, date_str) for station_id, date_str in requests]
            log.info(f"Starting async fetch for {len(tasks)} station-date combinations...")
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
