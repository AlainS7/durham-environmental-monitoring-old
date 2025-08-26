import pandas as pd
import pytest
from unittest.mock import MagicMock

from src.data_collection.daily_data_collector import insert_data_to_db, clean_and_transform_data
from typing import cast
from src.database.db_manager import HotDurhamDB

class DummyDB:
    def __init__(self):
        self.engine = MagicMock()
        self.engine.connect.return_value.__enter__.return_value = MagicMock()
        # stub insert
        self.inserted = None
    def insert_sensor_readings(self, df):
        self.inserted = df

@pytest.fixture
def deployment_map_df(monkeypatch):
    import pandas as pd
    # Patch read_sql to return deployments including SAPIENS
    def fake_read_sql(query, connection):
        return pd.DataFrame({
            'deployment_pk': [1],
            'native_sensor_id': ['SAPIENS_DEV_1'],
            'sensor_type': ['SAPIENS']
        })
    monkeypatch.setattr('pandas.read_sql', fake_read_sql)


def test_clean_and_insert_sapiens(deployment_map_df):
    raw = pd.DataFrame({
        'native_sensor_id': ['SAPIENS_DEV_1'],
        'timestamp': ['2025-07-27T12:00:00Z'],
        'temperature': [23.4],
        'humidity': [45.0],
        'pm2_5': [12.3]
    })
    cleaned = clean_and_transform_data(raw, 'SAPIENS')
    assert 'timestamp' in cleaned.columns
    db = DummyDB()
    # Cast for test scenario; production path uses real HotDurhamDB
    insert_data_to_db(cast(HotDurhamDB, db), pd.DataFrame(), pd.DataFrame(), cleaned)  # type: ignore[arg-type]
    assert db.inserted is not None
    out = db.inserted
    assert {'timestamp','deployment_fk','metric_name','value'}.issubset(out.columns)
    assert out['metric_name'].nunique() >= 1
