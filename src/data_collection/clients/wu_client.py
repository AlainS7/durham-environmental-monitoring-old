
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
        """
        if self.use_history_hourly_endpoint:
            # Use /history/hourly endpoint (per-day, per-station)
            endpoint = "history/hourly"
            # The date param for this endpoint is YYYYMMDD
            date_param = start_date.replace("-", "")
            params = {
                "stationId": station_id,
                "date": date_param,
                "format": "json",
                "apiKey": self.api_key,
                "units": "m",
                "numericPrecision": "decimal"
            }
            # /history/hourly is under /v2/pws, so base_url is the same
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
                    log.debug(f"[WUClient _fetch_one] DataFrame shape for station {station_id} on {start_date}: {df.shape}")
                    df['stationID'] = station_id
                    # Filter to just the requested date
                    if 'obsTimeUtc' in df.columns:
                        df['obsTimeUtc'] = pd.to_datetime(df['obsTimeUtc'])
                        date_start = pd.to_datetime(start_date).tz_localize('UTC')
                        date_end = date_start + pd.Timedelta(days=1)
                        mask = (df['obsTimeUtc'] >= date_start) & (df['obsTimeUtc'] < date_end)
                        df = df.loc[mask]
                    return df
            return None
        elif self.use_all_endpoint:
            endpoint = "observations/all"
            params = {
                "stationId": station_id,
                "format": "json",
                "apiKey": self.api_key,
                "units": "m",
                "startDate": start_date,  # YYYY-MM-DD
                "endDate": end_date if end_date else start_date  # YYYY-MM-DD
            }
            data = await self._request("GET", endpoint, params=params)
            if data and 'observations' in data:
                obs = data['observations']
                processed = []
                for o in obs:
                    metric = o.pop('metric', {}) if 'metric' in o and o['metric'] is not None else {}
                    processed.append({**o, **metric})
                if processed:
                    df = pd.DataFrame(processed)
                    log.debug(f"[WUClient _fetch_one] DataFrame shape for station {station_id} from {start_date} to {end_date}: {df.shape}")
                    df['stationID'] = station_id
                    if 'obsTimeUtc' in df.columns:
                        df['obsTimeUtc'] = pd.to_datetime(df['obsTimeUtc'])
                        date_start = pd.to_datetime(start_date).tz_localize('UTC')
                        date_end_str = end_date if end_date else start_date
                        date_end = pd.to_datetime(date_end_str).tz_localize('UTC') + pd.Timedelta(days=1)
                        mask = (df['obsTimeUtc'] >= date_start) & (df['obsTimeUtc'] < date_end)
                        df = df.loc[mask]
                    return df
            return None
        else:
            endpoint = "observations/all/1day"
            params = {
                "stationId": station_id,
                "format": "json",
                "apiKey": self.api_key,
                "units": "m"
            }
            data = await self._request("GET", endpoint, params=params)
            if data and 'observations' in data:
                obs = data['observations']
                processed = []
                for o in obs:
                    metric = o.pop('metric', {}) if 'metric' in o and o['metric'] is not None else {}
                    processed.append({**o, **metric})
                if processed:
                    df = pd.DataFrame(processed)
                    print(f"[WUClient _fetch_one] DataFrame shape for station {station_id} on {start_date}: {df.shape}")
                    df['stationID'] = station_id
                    if 'obsTimeUtc' in df.columns:
                        df['obsTimeUtc'] = pd.to_datetime(df['obsTimeUtc'])
                        date_start = pd.to_datetime(start_date).tz_localize('UTC')
                        date_end_str = end_date if end_date else start_date
                        date_end = pd.to_datetime(date_end_str).tz_localize('UTC') + pd.Timedelta(days=1)
                        mask = (df['obsTimeUtc'] >= date_start) & (df['obsTimeUtc'] < date_end)
                        df = df.loc[mask]
                    return df
            return None

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
