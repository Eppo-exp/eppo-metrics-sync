import pytest

from eppo_metrics_sync.validation import unique_names, valid_fact_references, aggregation_is_valid
from eppo_metrics_sync.eppo_metrics_sync import EppoMetricsSync


def test_dbt():
    eppo_metric_sync = EppoMetricsSync(
        'tests/yaml/dbt/valid', 
        schema_type='dbt-model', 
        dbt_model_prefix='test_db.test_schema'
    )
    eppo_metric_sync.read_yaml_files()
    eppo_metric_sync.validate()
