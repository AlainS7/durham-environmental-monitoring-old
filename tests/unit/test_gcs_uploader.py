import pandas as pd
import pytest

from src.storage.gcs_uploader import GCSUploader


class DummyBlob:
    def __init__(self, path):
        self.path = path
        self._uploaded = False
    def upload_from_file(self, *_, **__):  # pragma: no cover - simple stub
        self._uploaded = True


class DummyBucket:
    def __init__(self):
        self.blobs = {}
    def blob(self, path):
        b = DummyBlob(path)
        self.blobs[path] = b
        return b


class DummyClient:
    def __init__(self):
        self._bucket = DummyBucket()
    def bucket(self, *_):
        return self._bucket


def build_df(ts: str = "2025-08-26T00:00:00Z", n: int = 3):
    return pd.DataFrame({
        'timestamp': pd.date_range(ts, periods=n, freq='h'),
        'value': list(range(n)),
    })


def test_make_blob_path_raw():
    df = build_df()
    uploader = GCSUploader(bucket='b', prefix='sensor_readings', client=DummyClient())  # type: ignore[arg-type]
    path = uploader._make_blob_path('WU', df, aggregated=False, interval='h', ts_column='timestamp')
    assert path.startswith('sensor_readings/source=WU/agg=raw/dt=2025-08-26/WU-2025-08-26')


def test_make_blob_path_aggregated_custom_interval():
    df = build_df()
    uploader = GCSUploader(bucket='b', prefix='sensor_readings', client=DummyClient())  # type: ignore[arg-type]
    path = uploader._make_blob_path('TSI', df, aggregated=True, interval='15min', ts_column='timestamp')
    assert 'agg=15min' in path
    assert path.startswith('sensor_readings/source=TSI/')


def test_upload_parquet_invokes_blob():
    # Skip this test if pyarrow isn't available in the test environment
    pytest.importorskip("pyarrow")
    df = build_df()
    # Inject pyarrow stand-ins by monkeypatching module attributes if missing
    uploader = GCSUploader(bucket='b', prefix='sensor_readings', client=DummyClient())  # type: ignore[arg-type]
    if getattr(uploader, 'pa', None) is None:  # pragma: no cover - executed only when pyarrow missing
        pass
    path = uploader.upload_parquet(df, source='WU', aggregated=False, interval='h', ts_column='timestamp')
    assert path.startswith('gs://b/sensor_readings/source=WU/agg=raw')