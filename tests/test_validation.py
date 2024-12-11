import pytest
import re

from eppo_metrics_sync.validation import unique_names, valid_fact_references, aggregation_is_valid
from eppo_metrics_sync.eppo_metrics_sync import EppoMetricsSync

# If we use context.py we can do something like this instead
# from .context import eppo_metric_sync
# from .context import validation


test_yaml_dir = "tests/yaml/invalid"


def test_unique_fact_source_names():
    eppo_metrics_sync = EppoMetricsSync(directory=None)
    eppo_metrics_sync.load_eppo_yaml(
        path=test_yaml_dir + "/duplicated_fact_source_names.yaml")

    with pytest.raises(ValueError, match="Fact source names are not unique: upgrades_table"):
        eppo_metrics_sync.validate()


def test_unique_metric_names():
    eppo_metrics_sync = EppoMetricsSync(directory=None)
    eppo_metrics_sync.load_eppo_yaml(
        path=test_yaml_dir + "/duplicated_metric_names.yaml")

    with pytest.raises(ValueError, match="Metric names are not unique: Total Upgrades to Paid Plan"):
        eppo_metrics_sync.validate()


def test_unique_fact_names():
    eppo_metrics_sync = EppoMetricsSync(directory=None)
    eppo_metrics_sync.load_eppo_yaml(
        path=test_yaml_dir + "/duplicated_fact_names.yaml")

    with pytest.raises(ValueError, match="Fact names are not unique: upgrades"):
        eppo_metrics_sync.validate()


def test_valid_guardrail_cutoff_signs():
    eppo_metrics_sync = EppoMetricsSync(directory=None)
    eppo_metrics_sync.load_eppo_yaml(
        path=test_yaml_dir + "/invalid_guardrail_cutoff_sign.yaml")

    with pytest.raises(ValueError, match="Total Upgrades to Paid Plan is having invalid guardrail_cutoff sign: "
                                         "guardrail_cutoff value should be negative"):
        eppo_metrics_sync.validate()


"""def test_unique_fact_property_names():

    eppo_metrics_sync = EppoMetricsSync(directory = None)
    eppo_metrics_sync.load_yaml(
        path = test_yaml_dir + "/duplicated_fact_property_names.yaml")

    with pytest.raises(ValueError, match = "Fact property names are not unique: device"):
        eppo_metrics_sync.validate()"""


def test_invalid_fact_reference():
    eppo_metrics_sync = EppoMetricsSync(directory=None)
    eppo_metrics_sync.load_eppo_yaml(
        path=test_yaml_dir + "/invalid_fact_reference.yaml")
    with pytest.raises(ValueError, match=re.escape("Invalid fact reference(s): revenue")):
        eppo_metrics_sync.validate()


def test_invalid_winsorization_operation():
    test_agg = {
        'operation': 'distinct_entity',
        'winsorization_lower_percentile': 0.1
    }
    res = aggregation_is_valid(test_agg)
    assert res == 'Cannot winsorize a metric with operation distinct_entity'


def test_invalid_aggregation_for_timeframe():
    test_agg = {
        'operation': 'conversion',
        'aggregation_timeframe_end_value': 1,
        'aggregation_timeframe_unit': 'days',
        'conversion_threshold_days': 1
    }

    res = aggregation_is_valid(test_agg)
    assert res == 'Cannot specify aggregation_timeframe_end_value for operation conversion'


def test_invalid_timeframe_parameters():
    test_agg = {
        'operation': 'sum',
        'aggregation_timeframe_end_value': 1
    }

    expected_error = 'The aggregation_timeframe_unit must be set to use timeframe parameters.'

    res = aggregation_is_valid(test_agg)
    assert res == expected_error


def test_invalid_aggregation_parameter():
    test_agg = {
        'operation': 'sum',
        'retention_threshold_days': 1
    }

    res = aggregation_is_valid(test_agg)
    assert res == 'retention_threshold_days specified, but operation is sum'


def test_missing_conversion_threshold():
    test_agg = {
        'operation': 'conversion'
    }

    res = aggregation_is_valid(test_agg)
    assert res == 'conversion aggregation must have conversion_threshold_days set'


def test_extra_parameter_on_retention_metric():
    test_agg = {
        'operation': 'retention',
        'conversion_threshold_days': 2
    }

    res = aggregation_is_valid(test_agg)
    assert res == 'Invalid parameter for retention aggregation: conversion_threshold_days'


def test_count_distinct():
    test_agg = {
        'operation': 'count_distinct',
        'aggregation_timeframe_start_value': 1,
        'aggregation_timeframe_end_value': 7,
        'aggregation_timeframe_unit': 'days'
    }

    res = aggregation_is_valid(test_agg)
    assert res == None

def test_last_value():
    res = aggregation_is_valid({'operation': 'last_value'})
    assert res == None

def test_first_value():
    res = aggregation_is_valid({'operation': 'first_value'})
    assert res == None

def test_valid_yaml():
    eppo_metrics_sync = EppoMetricsSync(directory=None)
    eppo_metrics_sync.load_eppo_yaml(path='tests/yaml/valid/purchases.yaml')
    eppo_metrics_sync.validate()
