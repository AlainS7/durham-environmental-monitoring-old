"""Sapiens client integration.

This file was rewritten to repair indentation and typing issues introduced during
previous patch attempts. It provides a minimal, clean implementation patterned
after other sensor clients.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional

import pandas as pd
import pydantic

from .base_client import BaseClient

log = logging.getLogger(__name__)


class SapiensObservation(pydantic.BaseModel):
    """Single Sapiens observation (adjust fields to real API schema)."""

    device_id: str
    timestamp: datetime
    temperature_c: Optional[float] = None
    humidity_percent: Optional[float] = None
    pm2_5: Optional[float] = None
    pm10: Optional[float] = None
    co2_ppm: Optional[float] = None


class SapiensClient(BaseClient):
    """Client for Sapiens sensors."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.sapiens.example/v1",
        semaphore_limit: int = 5,
    ) -> None:
        super().__init__(base_url=base_url, api_key=api_key, semaphore_limit=semaphore_limit)
        self.headers: Optional[dict[str, str]] = None
        self.device_ids: List[str] = []  # To be populated externally

    async def _authenticate(self) -> bool:
        if self.api_key:
            self.headers = {"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"}
            return True
        log.error("Sapiens API key missing; cannot authenticate.")
        return False

    async def _fetch_one_day(self, device_id: str, date_iso: str) -> Optional[pd.DataFrame]:
        if not self.headers:
            log.error("Sapiens client not authenticated.")
            return None
        start_iso = f"{date_iso}T00:00:00Z"
        end_iso = (datetime.strptime(date_iso, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
        params = {"device_id": device_id, "start": start_iso, "end": end_iso}
        raw = await self._request("GET", "telemetry", params=params, headers=self.headers)
        if not raw:
            return None
        records: List[dict] = []
        for rec in raw:
            try:
                parsed = SapiensObservation.model_validate(rec)
                records.append(parsed.model_dump())
            except pydantic.ValidationError as e:  # pragma: no cover (warn path)
                log.warning(f"Sapiens validation error for device {device_id}: {e}")
        if not records:
            return None
        return pd.DataFrame(records)

    async def fetch_data(
        self,
        start_date: str,
        end_date: str,
        aggregate: bool = False,
        agg_interval: str = "h",
    ) -> pd.DataFrame:
        if not await self._authenticate():
            return pd.DataFrame()
        date_range = pd.date_range(start=start_date, end=end_date)
        tasks = [
            self._fetch_one_day(dev_id, d.strftime("%Y-%m-%d"))
            for dev_id in self.device_ids
            for d in date_range
        ]
        results: List[pd.DataFrame] = []
        for fut in asyncio.as_completed(tasks):
            df = await fut
            if df is not None:
                results.append(df)
        if not results:
            return pd.DataFrame()
        raw_df = pd.concat(results, ignore_index=True)
        if raw_df.empty:
            return raw_df

        # Standardize columns to align with downstream cleaning logic
        raw_df.rename(
            columns={
                "device_id": "native_sensor_id",
                "timestamp": "timestamp",
                "temperature_c": "temperature",
                "humidity_percent": "humidity",
                "pm2_5": "pm2_5",
                "pm10": "pm10",
            },
            inplace=True,
        )
        raw_df["timestamp"] = pd.to_datetime(raw_df["timestamp"], utc=True)
        if not aggregate:
            return raw_df

        # Aggregation: group by sensor id then resample to interval and average numeric columns
        indexed = raw_df.set_index("timestamp")
        grouped = indexed.groupby("native_sensor_id").resample(agg_interval)
        # mean() on grouped object returns numeric means; reset index to flat structure
        final_df = grouped.mean(numeric_only=True).reset_index()
        return final_df
