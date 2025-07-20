import json
import os
from functools import lru_cache
from src.config.app_config import app_config

@lru_cache(maxsize=None)
def load_sensor_configs():
    """
    Loads production and test sensor configurations from their respective files.
    Caches the result to avoid repeated file I/O.
    """
    # Correctly access the paths from app_config
    prod_config_path = app_config.sensor_config_paths.get('production')
    test_config_path = app_config.sensor_config_paths.get('test')
    
    prod_sensors = {}
    if prod_config_path and os.path.exists(prod_config_path):
        with open(prod_config_path, 'r') as f:
            prod_sensors = json.load(f)
            
    test_sensors = {}
    if test_config_path and os.path.exists(test_config_path):
        with open(test_config_path, 'r') as f:
            test_sensors = json.load(f)
            
    return prod_sensors, test_sensors

@lru_cache(maxsize=None)
def get_wu_stations():
    """
    Extracts WU station dictionaries from the production sensor configuration.
    """
    prod_sensors, _ = load_sensor_configs()
    # Ensure it returns the list of station dictionaries, not just IDs.
    return prod_sensors.get('wu', [])

@lru_cache(maxsize=None)
def get_tsi_devices():
    """
    Extracts TSI device IDs from the production sensor configuration.
    """
    prod_sensors, _ = load_sensor_configs()
    # Ensure we return a list of IDs, not a list of dicts
    return [device['id'] for device in prod_sensors.get('tsi', []) if 'id' in device]
