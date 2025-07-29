import pytest
import pandas as pd

# Use the main data collection process for integration testing
from src.data_collection.daily_data_collector import run_collection_process

@pytest.fixture
def sample_wu_df():
    """Creates a sample Weather Underground DataFrame for testing."""
    data = {
        'stationID': ['WU_PROD_01', 'WU_TEST_01', 'WU_PROD_02'],
        'tempAvg': [25, 26, 27]
    }
    return pd.DataFrame(data)

@pytest.fixture
def sample_tsi_df():
    """Creates a sample TSI DataFrame for testing."""
    data = {
        'device_id': ['TSI_PROD_X', 'TSI_PROD_Y', 'TSI_TEST_A'],
        'PM2.5': [10.1, 12.3, 15.5]
    }
    return pd.DataFrame(data)


# Integration test for the main data collection process


@pytest.mark.asyncio
async def test_main_script_flow(mocker, sample_wu_df, sample_tsi_df):
    """
    Integration test for the main data collection process.
    Mocks WUClient, TSIClient, and DB interactions to verify end-to-end logic.
    """
    # Mock WUClient and TSIClient fetch_data methods
    mock_wu_client = mocker.AsyncMock()
    mock_tsi_client = mocker.AsyncMock()
    mock_wu_client.fetch_data.return_value = sample_wu_df
    mock_tsi_client.fetch_data.return_value = sample_tsi_df

    mocker.patch('src.data_collection.daily_data_collector.WUClient', return_value=mock_wu_client)
    mocker.patch('src.data_collection.daily_data_collector.TSIClient', return_value=mock_tsi_client)

    # Mock DB and its insertion method
    mock_db_instance = mocker.MagicMock()
    mock_db_instance.insert_sensor_readings = mocker.MagicMock()
    mocker.patch('src.data_collection.daily_data_collector.HotDurhamDB', return_value=mock_db_instance)

    # Run the main collection process
    start_date = '2025-07-27'
    end_date = '2025-07-27'
    await run_collection_process(start_date, end_date, is_dry_run=False)

    # Assert that the clients were called
    mock_wu_client.fetch_data.assert_called_once_with(start_date, end_date)
    mock_tsi_client.fetch_data.assert_called_once_with(start_date, end_date)

    # Assert that the DB insertion was called
    mock_db_instance.insert_sensor_readings.assert_called_once()
