import io
import logging
from typing import Optional

import pandas as pd
from google.cloud import storage
try:
    import pyarrow as pa
    import pyarrow.parquet as pq
except Exception:  # pragma: no cover - import-time guard
    pa = None
    pq = None

log = logging.getLogger(__name__)


class GCSUploader:
    """Uploads pandas DataFrames to Google Cloud Storage as Parquet files.

    Paths are partitioned by date for efficient BigQuery batch loads.
    """

    def __init__(self, bucket: str, prefix: str = "sensor_readings"):
        if not bucket:
            raise ValueError("GCS bucket must be provided")
        self.bucket_name = bucket
        self.prefix = prefix.strip("/")
        self.client = storage.Client()
        self.bucket = self.client.bucket(self.bucket_name)

    def _make_blob_path(
        self,
        source: str,
        df: pd.DataFrame,
        aggregated: bool,
        interval: str,
        ts_column: str,
        extra_suffix: Optional[str] = None,
    ) -> str:
        if df.empty:
            raise ValueError("Cannot build path for empty DataFrame")
        ts = pd.to_datetime(df[ts_column]).sort_values().iloc[0]
        date_str = ts.strftime("%Y-%m-%d")
        agg_part = f"agg={interval}" if aggregated else "agg=raw"
        suffix = f"-{extra_suffix}" if extra_suffix else ""
        filename = f"{source}-{date_str}{suffix}.parquet"
        path = f"{self.prefix}/source={source}/{agg_part}/dt={date_str}/{filename}"
        return path

    def upload_parquet(
        self,
        df: pd.DataFrame,
        source: str,
        aggregated: bool = False,
        interval: str = "h",
        ts_column: str = "timestamp",
        extra_suffix: Optional[str] = None,
    ) -> str:
        """Write DataFrame as Parquet to GCS. Returns the GCS path.

        BigQuery best-practice: store wide flat tables for analytics. We'll keep
        the DataFrame as-is. Use external transformation to pivot if needed later.
        """
        if df.empty:
            log.info("Skipping upload: DataFrame is empty.")
            return ""
        # Ensure timestamp column exists and is datetime
        if ts_column not in df.columns:
            raise ValueError(f"DataFrame missing required timestamp column '{ts_column}'")
        df = df.copy()
        # Cope with duplicate column names which cause pyarrow.Table.from_pandas to fail.
        # Keep the first occurrence for each duplicate column name and warn.
        if df.columns.duplicated().any():
            dup_names = df.columns[df.columns.duplicated()].unique().tolist()
            log.warning(f"Duplicate column names found: {dup_names}. Keeping first occurrence of each and dropping duplicates.")
            df = df.loc[:, ~df.columns.duplicated()]
        df[ts_column] = pd.to_datetime(df[ts_column], utc=True, errors='coerce')
        df = df.dropna(subset=[ts_column])
        if df.empty:
            log.info("Skipping upload: DataFrame empty after timestamp coercion.")
            return ""

        blob_path = self._make_blob_path(source, df, aggregated, interval, ts_column, extra_suffix)
        log.info(f"Uploading Parquet to gs://{self.bucket_name}/{blob_path}...")

        # Write to in-memory buffer as parquet
        if pa is None or pq is None:
            raise RuntimeError("pyarrow is required for Parquet uploads. Please install pyarrow.")

        table = pa.Table.from_pandas(df)
        buf = io.BytesIO()
        pq.write_table(table, buf, compression="snappy")
        buf.seek(0)

        blob = self.bucket.blob(blob_path)
        blob.upload_from_file(buf, content_type="application/octet-stream")
        log.info("Upload complete.")
        return f"gs://{self.bucket_name}/{blob_path}"
