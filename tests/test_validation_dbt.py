import pytest

from eppo_metrics_sync.validation import unique_names, valid_fact_references, aggregation_is_valid
from eppo_metrics_sync.eppo_metrics_sync import EppoMetricsSync

test_yaml_dir = "tests/yaml/dbt/invalid"


def test_invalid_entity_tag():

    eppo_metrics_sync = EppoMetricsSync(
        directory = None, 
        schema_type = 'dbt-model',
        dbt_model_prefix = 'foo'
    )
    with pytest.raises(
        AssertionError, 
        match = "Invalid entity tag eppo_entity:anonymous_user:foo in model revenue"
        ):
        eppo_metrics_sync.load_dbt_yaml(path = test_yaml_dir + "/invalid_entity_tag.yml")


def test_missing_entity():

    eppo_metrics_sync = EppoMetricsSync(
        directory = None, 
        schema_type = 'dbt-model',
        dbt_model_prefix = 'foo'
    )
    with pytest.raises(
        ValueError, 
        match = 'At least 1 column must have tag "eppo_entity:<entity_name>"'
        ):
        eppo_metrics_sync.load_dbt_yaml(path = test_yaml_dir + "/missing_entity.yml")
    

def test_missing_timestamp():

    eppo_metrics_sync = EppoMetricsSync(
        directory = None, 
        schema_type = 'dbt-model',
        dbt_model_prefix = 'foo'
    )
    with pytest.raises(
        ValueError, 
        match = 'Exactly 1 column must be have tag "eppo_timestamp"'
        ):
        eppo_metrics_sync.load_dbt_yaml(path = test_yaml_dir + "/missing_timestamp.yml")

  
def test_overlapping_tags():

    eppo_metrics_sync = EppoMetricsSync(
        directory = None, 
        schema_type = 'dbt-model',
        dbt_model_prefix = 'foo'
    )
    with pytest.raises(
        ValueError, 
        match = 'The following columns had tags to multiple Eppo fields: gross_revenue'
        ):
        eppo_metrics_sync.load_dbt_yaml(path = test_yaml_dir + "/overlapping_tags.yml")

# test that package handles yml without 'models' member gracefully
def test_no_model_tag():

    eppo_metrics_sync = EppoMetricsSync(
        directory = None, 
        schema_type = 'dbt-model',
        dbt_model_prefix = 'foo'
    )
    eppo_metrics_sync.load_dbt_yaml(path = test_yaml_dir + "/no_model_tag.yml")
