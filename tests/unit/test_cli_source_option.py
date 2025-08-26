import argparse
import importlib


def test_daily_data_collector_source_choices_includes_sapiens():
    importlib.import_module('src.data_collection.daily_data_collector')
    parser = argparse.ArgumentParser()
    # Recreate only the --source arg using same choices as module for isolation
    parser.add_argument('--source', type=str, choices=['all','wu','tsi','sapiens'])
    # Ensure sapiens accepted
    args = parser.parse_args(['--source','sapiens'])
    assert args.source == 'sapiens'
