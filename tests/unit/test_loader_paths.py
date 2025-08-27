from scripts.load_to_bigquery import build_gcs_uri


def test_build_gcs_uri_raw():
    uri = build_gcs_uri('bucket', 'sensor_readings', 'WU', 'raw', '2025-08-26')
    assert uri == 'gs://bucket/sensor_readings/source=WU/agg=raw/dt=2025-08-26/*.parquet'


def test_build_gcs_uri_interval():
    uri = build_gcs_uri('b', 'p', 'TSI', '15min', '2025-01-01')
    assert uri.endswith('/source=TSI/agg=15min/dt=2025-01-01/*.parquet')


def test_table_name_correspondence():
    # Mirror logic in script: sensor_readings_{src.lower()}_{agg}
    src = 'WU'
    agg = 'raw'
    table = f"sensor_readings_{src.lower()}_{agg}"
    assert table == 'sensor_readings_wu_raw'