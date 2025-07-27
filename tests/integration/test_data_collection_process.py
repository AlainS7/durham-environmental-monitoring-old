
import pytest
import pandas as pd
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta

from src.data_collection.daily_data_collector import run_collection_process

@pytest.fixture
def mock_clients(mocker):
    """Mocks WUClient and TSIClient fetch_data methods."""
    mock_wu_client = AsyncMock()
    mock_tsi_client = AsyncMock()

    mocker.patch('src.data_collection.daily_data_collector.WUClient', return_value=mock_wu_client)
    mocker.patch('src.data_collection.daily_data_collector.TSIClient', return_value=mock_tsi_client)

    # Sample data for WUClient
    wu_data = {
        'stationID': ['KNCGARNE13'],
        'obsTimeUtc': ['2025-07-27T12:00:00Z'],
        'tempAvg': [25.0],
        'humidityAvg': [60.0]
    }
    mock_wu_client.fetch_data.return_value = pd.DataFrame(wu_data)

    # Sample data for TSIClient
    tsi_data = {
        'device_id': ['d14rfblfk2973f196c5g'],
        'timestamp': ['2025-07-27T12:00:00Z'],
        'mcpm2x5': [15.5],
        'temp_c': [26.0],
        'rh_percent': [55.0]
    }
    mock_tsi_client.fetch_data.return_value = pd.DataFrame(tsi_data)

    return mock_wu_client, mock_tsi_client

@pytest.fixture
def mock_db(mocker):
    """Mocks HotDurhamDB and its engine interactions."""
    mock_db_instance = MagicMock()
    mock_engine = MagicMock()
    mock_connection = MagicMock()
    mock_connection.execute = MagicMock() # Explicitly mock the execute method
    mock_transaction = MagicMock()

    mock_db_instance.engine = mock_engine
    mock_engine.connect.return_value.__enter__.return_value = mock_connection
    mock_connection.begin.return_value.__enter__.return_value = mock_transaction

    mocker.patch('src.data_collection.daily_data_collector.HotDurhamDB', return_value=mock_db_instance)
    mocker.patch('pandas.read_sql', return_value=pd.DataFrame({
        'deployment_pk': [1, 2],
        'native_sensor_id': ['KNCGARNE13', 'd14rfblfk2973f196c5g'],
        'sensor_type': ['WU', 'TSI']
    }))
    mocker.patch('pandas.DataFrame.to_sql')

    return mock_db_instance, mock_connection

@pytest.mark.asyncio
async def test_run_collection_process_success(mock_clients, mock_db):
    """Test successful execution of the data collection process."""
    mock_wu_client, mock_tsi_client = mock_clients
    mock_db_instance, mock_connection = mock_db

    start_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    end_date = start_date

    await run_collection_process(start_date, end_date, is_dry_run=False)

    # Verify clients were called
    mock_wu_client.fetch_data.assert_called_once_with(start_date, end_date, False)
    mock_tsi_client.fetch_data.assert_called_once_with(start_date, end_date)

    # Verify database interactions
    assert mock_connection.execute.call_count == 2 # For the DROP TABLE statement
    pd.DataFrame.to_sql.assert_called_once() # For the temporary table creation

    # Further assertions can be added here to inspect the arguments passed to to_sql
    # For example, to check the content of the DataFrame passed to to_sql:
    # assert pd.DataFrame.to_sql.call_args[0][0].shape[0] > 0
