"""Unit tests for scripts/bq_upload_sample.py"""
from unittest.mock import patch, MagicMock

from scripts.bq_upload_sample import build_sample_df, upload_to_bigquery


def test_build_sample_df():
    df = build_sample_df()
    assert not df.empty
    assert set(df.columns) == {"timestamp", "deployment_fk", "metric_name", "value"}


@patch("scripts.bq_upload_sample.bigquery.Client")
def test_upload_to_bigquery_dry_run(mock_client):
    df = build_sample_df()
    assert upload_to_bigquery(df, "some_ds", "some_table", dry_run=True) is True
    # ensure client not created when dry run
    mock_client.assert_not_called()


@patch("scripts.bq_upload_sample.bigquery.Client")
def test_upload_to_bigquery_real(mock_client):
    mock_instance = MagicMock()
    mock_client.return_value = mock_instance
    # mock dataset/table interactions
    mock_instance.get_dataset.side_effect = Exception("not found")
    mock_instance.create_dataset.return_value = True
    mock_job = MagicMock()
    mock_job.result.return_value = None
    mock_instance.load_table_from_dataframe.return_value = mock_job

    df = build_sample_df()
    assert upload_to_bigquery(df, "ds", "tbl", dry_run=False) is True
    mock_client.assert_called_once()
    mock_instance.load_table_from_dataframe.assert_called_once()
