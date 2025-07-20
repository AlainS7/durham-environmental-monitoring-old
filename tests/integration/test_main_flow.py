import pytest
import pandas as pd
import asyncio
from unittest.mock import call

# It's better to import the module and patch its functions
from src.data_collection import faster_wu_tsi_to_sheets_async as data_collection_script

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

@pytest.mark.asyncio
async def test_main_script_flow(mocker, sample_wu_df, sample_tsi_df):
    """
    Integration test for the main script flow.
    Mocks API fetching and database insertion to verify the end-to-end logic.
    """
    # 1. Mock the external dependencies
    
    # Mock the API fetchers to return our sample data
    mock_fetch_wu = mocker.patch.object(data_collection_script, 'fetch_wu_data_async', return_value=sample_wu_df)
    # TSI fetcher returns a tuple (df, per_device_dict)
    mock_fetch_tsi = mocker.patch.object(data_collection_script, 'fetch_tsi_data_async', return_value=(sample_tsi_df, {}))
    
    # Mock the database insertion function so we can check what it's called with
    mock_insert_db = mocker.patch.object(data_collection_script, 'insert_data_to_db')
    
    # Mock the TestSensorConfig, similar to the unit test
    test_sensor_ids = {'WU_TEST_01', 'TSI_TEST_A'}
    mock_config_instance = mocker.MagicMock()
    mock_config_instance.is_test_sensor.side_effect = lambda sensor_id: sensor_id in test_sensor_ids
    mocker.patch.object(data_collection_script, 'TestSensorConfig', return_value=mock_config_instance)

    # 2. Run the main function of the script
    await data_collection_script.main()

    # 3. Assert that the mocks were called correctly

    # Check that the API fetchers were called
    mock_fetch_wu.assert_called_once()
    mock_fetch_tsi.assert_called_once()

    # Check that insert_data_to_db was called twice (once for WU, once for TSI)
    assert mock_insert_db.call_count == 2

    # Get the arguments from the calls to the mock database function
    call_args = mock_insert_db.call_args_list
    
    # Find the call for 'wu_data' and the call for 'tsi_data'
    wu_call = next((c for c in call_args if c.args[1] == 'wu_data'), None)
    tsi_call = next((c for c in call_args if c.args[1] == 'tsi_data'), None)

    assert wu_call is not None, "insert_data_to_db was not called for 'wu_data'"
    assert tsi_call is not None, "insert_data_to_db was not called for 'tsi_data'"

    # Extract the DataFrames passed to the database function
    prod_wu_df_sent_to_db = wu_call.args[0]
    prod_tsi_df_sent_to_db = tsi_call.args[0]

    # Assert on the WU data sent to the database
    assert len(prod_wu_df_sent_to_db) == 2
    assert set(prod_wu_df_sent_to_db['stationID']) == {'WU_PROD_01', 'WU_PROD_02'}

    # Assert on the TSI data sent to the database
    assert len(prod_tsi_df_sent_to_db) == 2
    assert set(prod_tsi_df_sent_to_db['device_id']) == {'TSI_PROD_X', 'TSI_PROD_Y'}
