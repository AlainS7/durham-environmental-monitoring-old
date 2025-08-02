
import asyncio
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
import pydantic

from .base_client import BaseClient
from src.utils.config_loader import get_tsi_devices
from src.data_collection.models import TSIFlatRecord

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
        """Authenticates with the TSI API to get an access token using the managed httpx.AsyncClient."""
        params = {'grant_type': 'client_credentials'}
        data = {'client_id': self.client_id, 'client_secret': self.client_secret}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        if not self.client:
            log.error("TSIClient httpx.AsyncClient not initialized. Use TSIClient within an 'async with' block.")
            return False
        try:
            log.info("Trying TSI authentication with params and form-encoded body using managed client...")
            auth_resp = await self.client.post(self.auth_url, params=params, data=data, headers=headers)
            auth_resp.raise_for_status()
            auth_json = auth_resp.json()
            self.headers = {"Authorization": f"Bearer {auth_json['access_token']}", "Accept": "application/json"}
            log.info("TSI authentication succeeded with params and form-encoded body.")
            return True
        except Exception as e:
            log.error(f"TSI authentication failed: {e}", exc_info=True)
            return False

    async def _fetch_one_day(self, device_id: str, date_iso: str) -> Optional[pd.DataFrame]:
        """Fetches data for a single device and day using the flat-format endpoint."""
        if not self.headers:
            log.error("TSI client is not authenticated.")
            return None

        start_iso = f"{date_iso}T00:00:00Z"
        end_iso = (datetime.strptime(date_iso, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
        params = {'device_id': device_id, 'start_date': start_iso, 'end_date': end_iso}

        # Use the flat-format endpoint
        records = await self._request("GET", "telemetry/flat-format", params=params, headers=self.headers)
        if records:
            validated_records = []
            for rec in records:
                try:
                    validated = TSIFlatRecord.model_validate(rec)
                    validated_records.append(validated.model_dump())
                except pydantic.ValidationError as e:
                    log.error(f"TSI API response validation failed for record: {e}")
            if not validated_records:
                return None
            df = pd.DataFrame(validated_records)
            # Rename cloud_timestamp to timestamp for downstream compatibility
            if 'cloud_timestamp' in df.columns:
                df = df.rename(columns={'cloud_timestamp': 'timestamp'})
            df['device_id'] = device_id
            return df
        return None

    async def fetch_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetches TSI data for a given date range and aggregates it into hourly summaries.
        """
        if not await self._authenticate():
            log.error("TSI authentication failed. No data will be fetched.")
            return pd.DataFrame()

        log.info("Building list of requests for all devices and dates...")
        date_range = pd.date_range(start=start_date, end=end_date)
        requests = [(dev_id, d.strftime("%Y-%m-%d")) for dev_id in self.device_ids for d in date_range]
        tasks = [self._fetch_one_day(dev_id, date_str) for dev_id, date_str in requests]

        log.info(f"Starting async fetch for {len(tasks)} device-date combinations...")
        all_results = []
        from tqdm import tqdm
        for future in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Fetching TSI Data"):
            result = await future
            if result is not None:
                all_results.append(result)

        log.info(f"Fetched data for {len(all_results)} device-date combinations.")

        if not all_results:
            log.warning("No data fetched from TSI API.")
            return pd.DataFrame()

        log.info("Concatenating all results into a single DataFrame...")
        raw_df = pd.concat(all_results, ignore_index=True)
        if raw_df.empty or 'timestamp' not in raw_df.columns:
            log.warning("No valid data after concatenation.")
            return pd.DataFrame()

        log.info("Converting timestamp to datetime and setting as index...")
        raw_df['timestamp'] = pd.to_datetime(raw_df['timestamp'])
        raw_df.set_index('timestamp', inplace=True)

        log.info("Preparing aggregation dictionary for hourly resampling...")
        numeric_cols = raw_df.select_dtypes(include='number').columns.tolist()
        agg_dict = {col: 'mean' for col in numeric_cols}

        log.info("Starting groupby and hourly resampling...")
        final_df = raw_df.groupby('device_id').resample('h').agg(agg_dict)  # type: ignore

        log.info("Resetting index after resampling...")
        final_df = final_df.reset_index()

        log.info(f"Successfully resampled TSI data to {len(final_df)} hourly records.")
        return final_df
