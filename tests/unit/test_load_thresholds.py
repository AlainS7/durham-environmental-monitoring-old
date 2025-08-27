import json
from scripts.check_row_thresholds import load_thresholds, DEFAULT_THRESHOLDS

def test_load_thresholds_yaml_overrides(tmp_path, monkeypatch):
    # create YAML config overriding one value and adding new table
    yaml_content = """
row_thresholds:
  sensor_readings_wu_raw: 5
  new_table: 7
""".strip()
    cfg = tmp_path / 'data_quality.yaml'
    cfg.write_text(yaml_content)
    # run loader
    thresholds = load_thresholds(str(cfg), None)
    assert thresholds['sensor_readings_wu_raw'] == 5
    assert thresholds['new_table'] == 7
    # untouched default preserved
    assert thresholds['sensor_readings_tsi_raw'] == DEFAULT_THRESHOLDS['sensor_readings_tsi_raw']

def test_load_thresholds_json_precedence(tmp_path):
    # YAML sets value to 10, JSON should override to 3
    yaml_content = """
row_thresholds:
  sensor_readings_wu_raw: 10
""".strip()
    cfg = tmp_path / 'data_quality.yaml'
    cfg.write_text(yaml_content)
    json_override = tmp_path / 'override.json'
    json_override.write_text(json.dumps({'sensor_readings_wu_raw': 3}))
    thresholds = load_thresholds(str(cfg), str(json_override))
    assert thresholds['sensor_readings_wu_raw'] == 3

def test_load_thresholds_missing_yaml(monkeypatch):
    # no file, should just return defaults
    thresholds = load_thresholds('nonexistent.yaml', None)
    for k,v in DEFAULT_THRESHOLDS.items():
        assert thresholds[k] == v
