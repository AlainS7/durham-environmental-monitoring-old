import importlib.util
import pathlib

SCRIPT_PATH = pathlib.Path('scripts/merge_sensor_readings.py')

spec = importlib.util.spec_from_file_location('merge_sensor_readings', SCRIPT_PATH)
assert spec is not None
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)  # type: ignore
mod = module


def test_build_merge_sql_basic():
    sql = mod.build_merge_sql('proj', 'ds', 'stg', 'tgt', '2025-08-20', update_if_changed=False)
    assert 'WHEN MATCHED AND TRUE THEN UPDATE' in sql
    assert 'stg' in sql and 'tgt' in sql
    # Parameter marker present (@d)
    assert '@d' in sql


def test_build_merge_sql_changed_only():
    sql = mod.build_merge_sql('proj', 'ds', 'stg', 'tgt', '2025-08-20', update_if_changed=True)
    assert 'WHEN MATCHED AND T.value != S.value THEN UPDATE' in sql
    # Ensure no stray TRUE predicate
    assert 'AND TRUE THEN UPDATE' not in sql

