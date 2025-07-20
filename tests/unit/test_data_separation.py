import pandas as pd
import pytest
from unittest.mock import MagicMock
from data_collection.faster_wu_tsi_to_sheets_async import separate_sensor_data_by_type

@pytest.fixture
def mock_test_sensor_config(mocker):
    """Mocks the TestSensorConfig to control which sensors are 'test' sensors."""
    # Define the set of sensor IDs that should be considered 'test' sensors
    test_sensor_ids = {'WU_TEST_01', 'TSI_TEST_A'}
    
    # Create a mock instance of the TestSensorConfig class
    mock_config_instance = MagicMock()
    
    # Configure the 'is_test_sensor' method on the mock instance.
    # It will return True if the sensor_id is in our test_sensor_ids set, and False otherwise.
    mock_config_instance.is_test_sensor.side_effect = lambda sensor_id: sensor_id in test_sensor_ids
    
    # Use mocker to patch the TestSensorConfig class in the module where it's used.
    # The path should not include `src`.
    mocker.patch('data_collection.faster_wu_tsi_to_sheets_async.TestSensorConfig', return_value=mock_config_instance)
    
    return mock_config_instance

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

def test_separate_sensor_data_by_type(mock_test_sensor_config, sample_wu_df, sample_tsi_df):
    """
    Tests the data separation logic to ensure it correctly categorizes
    sensors into 'test' and 'production' based on the mocked config.
    """
    # Act: Call the function with the sample data
    test_data, prod_data = separate_sensor_data_by_type(sample_wu_df, sample_tsi_df)

    # Assert: Check the results for Weather Underground data
    # Check that the production WU DataFrame has 2 records
    assert len(prod_data['wu']) == 2
    # Check that the station IDs in the production data are correct
    assert set(prod_data['wu']['stationID']) == {'WU_PROD_01', 'WU_PROD_02'}
    
    # Check that the test WU DataFrame has 1 record
    assert len(test_data['wu']) == 1
    # Check that the station ID in the test data is correct
    assert test_data['wu']['stationID'].iloc[0] == 'WU_TEST_01'

    # Assert: Check the results for TSI data
    # Check that the production TSI DataFrame has 2 records
    assert len(prod_data['tsi']) == 2
    # Check that the device IDs in the production data are correct
    assert set(prod_data['tsi']['device_id']) == {'TSI_PROD_X', 'TSI_PROD_Y'}

    # Check that the test TSI DataFrame has 1 record
    assert len(test_data['tsi']) == 1
    # Check that the device ID in the test data is correct
    assert test_data['tsi']['device_id'].iloc[0] == 'TSI_TEST_A'

def test_separation_with_empty_dataframes(mock_test_sensor_config):
    """Tests that the function handles empty DataFrames gracefully."""
    # The mock_test_sensor_config fixture is needed to patch TestSensorConfig
    # even if we don't use it directly in the test.
    test_data, prod_data = separate_sensor_data_by_type(pd.DataFrame(), pd.DataFrame())
    
    assert test_data['wu'] is None
    assert test_data['tsi'] is None
    assert prod_data['wu'] is None
    assert prod_data['tsi'] is None
