
import asyncio
import pandas as pd
import logging
from datetime import datetime
from typing import Dict, Optional

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
        """Fetches data for a single device and day using the telemetry endpoint with start_date and end_date parameters."""
        if not self.headers:
            log.error("TSI client is not authenticated.")
            return None

        # Use start_date and end_date parameters in RFC3339 format (required for historical data with measurements)
        # This is the key difference - age parameter returns empty sensor arrays, but start_date/end_date returns full measurements
        from datetime import timedelta
        
        start_iso = f"{date_iso}T00:00:00Z"
        target_date = datetime.strptime(date_iso, "%Y-%m-%d")
        end_date = target_date + timedelta(days=1)
        end_iso = end_date.strftime("%Y-%m-%dT00:00:00Z")
        
        # Use start_date and end_date instead of age to get actual measurement data
        params = {'device_id': device_id, 'start_date': start_iso, 'end_date': end_iso}

        # Use the telemetry endpoint with start_date/end_date to get nested sensor measurements
        records = await self._request("GET", "telemetry", params=params, headers=self.headers)
        log.info(f"TSI RAW API RESPONSE for device {device_id} date {date_iso} (start={start_iso}, end={end_iso}): received {len(records) if records else 0} records")
        
        if not records:
            log.info(f"TSI API returned no records for device {device_id} date {date_iso}.")
            return None
        
        # Parse nested sensor measurements from telemetry response
        data = []
        for row in records:
            timestamp = row.get('cloud_timestamp')
            if not timestamp:
                continue
            
            # Extract metadata from record
            metadata = row.get('metadata', {})
            location = metadata.get('location', {})
            latitude = location.get('latitude')
            longitude = location.get('longitude')
            is_indoor = metadata.get('is_indoor')
            is_public = metadata.get('is_public')
            friendly_name = metadata.get('friendly_name')
            model = row.get('model')
            cloud_account_id = row.get('cloud_account_id')
            
            # Initialize all sensor values
            pm_1_0 = None
            pm_2_5 = None
            pm_4_0 = None
            pm_10 = None
            pm2_5_aqi = None
            pm10_aqi = None
            ncpm0_5 = None
            ncpm1_0 = None
            ncpm2_5 = None
            ncpm4_0 = None
            ncpm10 = None
            temp = None
            rh = None
            tpsize = None
            co2_ppm = None
            co_ppm = None
            baro_inhg = None
            o3_ppb = None
            no2_ppb = None
            so2_ppb = None
            ch2o_ppb = None
            voc_mgm3 = None
            
            # Extract measurements from nested sensors array
            sensors = row.get('sensors', [])
            for sensor in sensors:
                serial = sensor.get('serial')  # Get serial from first sensor
                measurements = sensor.get('measurements', [])
                for measurement in measurements:
                    name = measurement.get('name', '')
                    value = measurement.get('data', {}).get('value')
                    
                    # Map measurement names to fields
                    if name == 'PM 1.0':
                        pm_1_0 = value
                    elif name == 'PM 2.5':
                        pm_2_5 = value
                    elif name == 'PM 4.0':
                        pm_4_0 = value
                    elif name == 'PM 10':
                        pm_10 = value
                    elif name == 'PM 2.5 AQI':
                        pm2_5_aqi = value
                    elif name == 'PM 10 AQI':
                        pm10_aqi = value
                    elif name == 'NC 0.5':
                        ncpm0_5 = value
                    elif name == 'NC 1.0':
                        ncpm1_0 = value
                    elif name == 'NC 2.5':
                        ncpm2_5 = value
                    elif name == 'NC 4.0':
                        ncpm4_0 = value
                    elif name == 'NC 10':
                        ncpm10 = value
                    elif name == 'Temperature':
                        temp = value
                    elif name == 'Relative Humidity':
                        rh = value
                    elif name == 'Typical Particle Size':
                        tpsize = value
                    elif name == 'CO2':
                        co2_ppm = value
                    elif name == 'CO':
                        co_ppm = value
                    elif name == 'Barometric Pressure':
                        baro_inhg = value
                    elif name == 'O3':
                        o3_ppb = value
                    elif name == 'NO2':
                        no2_ppb = value
                    elif name == 'SO2':
                        so2_ppb = value
                    elif name == 'CH2O':
                        ch2o_ppb = value
                    elif name == 'VOC':
                        voc_mgm3 = value
            
            data.append({
                'timestamp': timestamp,
                'cloud_account_id': cloud_account_id,
                'device_id': device_id,
                'model': model,
                'serial': serial if 'serial' in locals() else None,
                'latitude': latitude,
                'longitude': longitude,
                'is_indoor': is_indoor,
                'is_public': is_public,
                'pm1_0': pm_1_0,
                'pm2_5': pm_2_5,
                'pm4_0': pm_4_0,
                'pm10': pm_10,
                'pm2_5_aqi': pm2_5_aqi,
                'pm10_aqi': pm10_aqi,
                'ncpm0_5': ncpm0_5,
                'ncpm1_0': ncpm1_0,
                'ncpm2_5': ncpm2_5,
                'ncpm4_0': ncpm4_0,
                'ncpm10': ncpm10,
                'temperature': temp,
                'rh': rh,
                'tpsize': tpsize,
                'co2_ppm': co2_ppm,
                'co_ppm': co_ppm,
                'baro_inhg': baro_inhg,
                'o3_ppb': o3_ppb,
                'no2_ppb': no2_ppb,
                'so2_ppb': so2_ppb,
                'ch2o_ppb': ch2o_ppb,
                'voc_mgm3': voc_mgm3
            })
        
        if not data:
            log.info(f"No valid sensor measurements found for device {device_id} date {date_iso}.")
            return None
        
        df = pd.DataFrame(data)
        log.info(f"TSI DataFrame for device {device_id} date {date_iso}: shape={df.shape}")
        log.debug(f"TSI columns: {list(df.columns)}\nSample:\n{df.head().to_string(index=False)}")
        
        # Convert timestamp using pandas' flexible ISO8601 parser
        df['timestamp'] = pd.to_datetime(df['timestamp'], format='ISO8601', utc=True)
        
        # Filter to only include records from the target date
        df = df[df['timestamp'].dt.date == target_date.date()]
        
        if df.empty:
            log.info(f"No data for target date {date_iso} after filtering (start_date/end_date returned data from other dates).")
            return None
        
        log.info(f"After filtering to {date_iso}: {len(df)} records remain")
        return df

    async def fetch_data(self, start_date: str, end_date: str, aggregate: bool = False, agg_interval: str = 'h') -> pd.DataFrame:
        """
        Fetches TSI data for a given date range, optionally aggregates into summaries.
        When aggregate is False, returns raw flat-format observations with a 'timestamp' column.
        """
        if not await self._authenticate():
            log.error("TSI authentication failed. No data will be fetched.")
            return pd.DataFrame()

        log.info("Building list of requests for all devices and dates...")
        date_range = pd.date_range(start=start_date, end=end_date)
        requests = [(dev_id, d.strftime("%Y-%m-%d")) for dev_id in self.device_ids for d in date_range]
        tasks = [self._fetch_one_day(dev_id, date_str) for dev_id, date_str in requests]

        log.info(f"Starting async fetch for {len(tasks)} device-date combinations...")
        all_results: list[pd.DataFrame] = []
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

        log.info("Converting timestamp to datetime...")
        raw_df['timestamp'] = pd.to_datetime(raw_df['timestamp'])
        # Drop rows with missing timestamps to avoid NaTType errors during resampling
        raw_df = raw_df.dropna(subset=['timestamp'])
        if raw_df.empty:
            log.warning("No valid data after dropping rows with missing timestamps.")
            return pd.DataFrame()

        if not aggregate:
            log.info("Aggregation disabled; returning raw TSI DataFrame.")
            return raw_df

        # Aggregation path
        raw_df = raw_df.set_index('timestamp')
        numeric_cols = raw_df.select_dtypes(include='number').columns.tolist()
        agg_dict = {col: 'mean' for col in numeric_cols}
        final_df = raw_df.groupby('device_id').resample(agg_interval).agg(agg_dict)  # type: ignore
        final_df = final_df.reset_index()
        log.info(f"Successfully resampled TSI data to {len(final_df)} records at interval '{agg_interval}'.")
        return final_df
