
import pytest
from unittest.mock import MagicMock, patch

from src.data_collection.clients.wu_client import WUClient
from src.data_collection.clients.tsi_client import TSIClient

@pytest.fixture
def mock_app_config():
    """Fixture to mock the app_config object globally."""
    with patch('src.config.app_config.app_config', MagicMock()) as mock_config:
        mock_config.wu_api_config = {'api_key': 'test_key', 'base_url': 'https://fake-wu.com'}
        mock_config.tsi_api_config = {
            'client_id': 'test_id',
            'client_secret': 'test_secret',
            'auth_url': 'https://fake-tsi.com/auth',
            'base_url': 'https://fake-tsi.com/api'
        }
        yield mock_config

@pytest.mark.asyncio
async def test_wu_client_fetch_data_success(mocker):
    """Test successful data fetching for WUClient."""
    mock_response = {
        'observations': [
            {'stationID': 'KNCGARNE13', 'obsTimeUtc': '2025-07-27T12:00:00Z', 'tempAvg': 25.0, 'humidityAvg': 60.0}
        ]
    }
    
    mocker.patch('src.data_collection.clients.base_client.BaseClient._request', return_value=mock_response)
    mocker.patch('src.data_collection.clients.wu_client.get_wu_stations', return_value=[{'stationId': 'KNCGARNE13'}])

    client = WUClient(api_key='test_key', base_url='https://fake-wu.com')
    df = await client.fetch_data('2025-07-27', '2025-07-27')

    assert not df.empty
    assert df.iloc[0]['stationID'] == 'KNCGARNE13'
    assert df.iloc[0]['tempAvg'] == 25.0

@pytest.mark.asyncio
async def test_tsi_client_fetch_data_success(mocker):
    """Test successful data fetching for TSIClient."""
    telemetry_response = [
        {
            'cloud_device_id': 'd14rfblfk2973f196c5g',
            # Provide field as 'timestamp' to exercise alias mapping and downstream rename logic deterministically
            'timestamp': '2025-07-27T12:00:00Z',
            'mcpm2x5': 15.5,
            'temperature': 26.0,
            'rh': 55.0
        }
    ]
    # Ensure the returned device list aligns with expectation in assertions
    mocker.patch('src.data_collection.clients.tsi_client.get_tsi_devices', return_value=['12345'])
    client = TSIClient(client_id='test_id', client_secret='test_secret', auth_url='https://fake-tsi.com/auth', base_url='https://fake-tsi.com/api')
    mocker.patch.object(client, '_authenticate', side_effect=lambda: setattr(client, 'headers', {"Authorization": "Bearer fake_token", "Accept": "application/json"}) or True)
    mocker.patch('src.data_collection.clients.base_client.BaseClient._request', return_value=telemetry_response)
    df = await client.fetch_data('2025-07-27', '2025-07-27')

    assert not df.empty
    assert not df.empty, "TSI DataFrame should not be empty"
    assert 'timestamp' in df.columns, "Timestamp column should be present after rename"
    assert (df['device_id'] == '12345').all(), "All rows should have the test device id"
    assert df.iloc[0]['mcpm2x5'] == 15.5
