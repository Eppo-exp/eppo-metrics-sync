import json
import jsonschema
import os
import requests

from eppo_metrics_sync.validation import (
    unique_names,
    valid_fact_references,
    metric_aggregation_is_valid,
    valid_guardrail_cutoff_signs,
    valid_experiment_computation
)

from eppo_metrics_sync.dbt_model_parser import DbtModelParser
from eppo_metrics_sync.helper import load_yaml

host = os.getenv('EPPO_API_HOST', 'https://eppo.cloud')
API_ENDPOINT = f'{host}/api/v1/metrics/sync'

class EppoMetricsSync:
    def __init__(
            self,
            directory,
            schema_type='eppo',
            dbt_model_prefix=None,
            sync_prefix=None,
            allow_upgrades=False
    ):
        self.directory = directory
        self.fact_sources = []
        self.metrics = []
        self.validation_errors = []
        self.schema_type = schema_type
        self.dbt_model_prefix = dbt_model_prefix
        self.sync_prefix = sync_prefix
        self.allow_upgrades = allow_upgrades

        # temporary: ideally would pull this from Eppo API
        package_root = os.path.dirname(os.path.abspath(__file__))
        schema_path = os.path.join(package_root, 'schema', 'eppo_metric_schema.json')
        with open(schema_path) as schema_file:
            self.schema = json.load(schema_file)

    def load_eppo_yaml(self, path):
        yaml_data = load_yaml(path)
        if 'fact_sources' in yaml_data:
            self.fact_sources.extend(yaml_data['fact_sources'])
        if 'metrics' in yaml_data:
            self.metrics.extend(yaml_data['metrics'])

    def load_dbt_yaml(self, path):
        if not self.dbt_model_prefix:
            raise ValueError('Must specify dbt_model_prefix when schema_type=dbt-model')
        yaml_data = load_yaml(path)
        models = yaml_data.get('models')
        if models:
            for model in models:
                dbt_model_parser = DbtModelParser(model, self.dbt_model_prefix).build()
                if dbt_model_parser:
                    self.fact_sources.append(dbt_model_parser)

    def yaml_is_valid(self, yaml_path):
        """
        Validate a single YAML file against the schema

        """
        data = load_yaml(yaml_path)
        try:
            jsonschema.validate(data, self.schema)
            return {"passed": True}
        except jsonschema.exceptions.ValidationError as e:
            return {"passed": False, "error_message": e}

    def read_yaml_files(self):
        # Recursively scan the directory for YAML files and load valid ones
        for root, _, files in os.walk(self.directory):
            for file in files:
                if file.endswith(".yaml") or file.endswith(".yml"):

                    yaml_path = os.path.join(root, file)

                    if self.schema_type == 'eppo':
                        valid = self.yaml_is_valid(yaml_path)
                        if valid['passed']:
                            self.load_eppo_yaml(yaml_path)
                        else:
                            self.validation_errors.append(
                                f"Schema violation in {yaml_path}: \n{valid['error_message']}"
                            )

                    elif self.schema_type == 'dbt-model':
                        self.load_dbt_yaml(yaml_path)

                    else:
                        raise ValueError(f'Unexpected schema_type: {self.schema_type}')

        if len(self.fact_sources) == 0 and len(self.metrics) == 0:
            raise ValueError(
                'No valid yaml files found. ' + ', '.join(self.validation_errors)
            )

    def _add_sync_prefix(self):
        for source in self.fact_sources:
            source['name'] = f"[{self.sync_prefix}] {source['name']}"

        for metric in self.metrics:
            metric['name'] = f"[{self.sync_prefix}] {metric['name']}"

    def validate(self):

        if len(self.fact_sources) == 0 and len(self.metrics) == 0:
            raise ValueError('No fact sources or metrics found, did you call eppo_metrics.read_yaml_files()?')

        unique_names(self)
        valid_fact_references(self)
        metric_aggregation_is_valid(self)
        valid_guardrail_cutoff_signs(self)
        valid_experiment_computation(self)

        if self.validation_errors:
            error_count = len(self.validation_errors)
            error_message = f"Validation failed with {error_count} error(s): \n"
            error_message += '\n'.join(self.validation_errors)
            raise ValueError(error_message)

        return True

    def _determine_sync_tag(self):
        if self.sync_prefix is not None:
            return self.sync_prefix

        return os.getenv('EPPO_SYNC_TAG')

    def _attach_reference_url(self, payload):
        """
        Optionally attach reference url to the payload if one exists
        """

        reference_url = os.getenv('EPPO_REFERENCE_URL')
        if not reference_url:
            return payload
        
        payload["reference_url"] = reference_url
        return payload

    def sync(self):
        self.read_yaml_files()
        if self.sync_prefix is not None:
            self._add_sync_prefix()
        self.validate()

        api_key = os.getenv('EPPO_API_KEY')
        if not api_key:
            raise Exception('EPPO_API_KEY not set in environment variables. Please set and try again')

        sync_tag = self._determine_sync_tag()
        if not sync_tag:
            raise Exception('EPPO_SYNC_TAG not set in environment variables. Please set and try again')

        headers = {"X-Eppo-Token": api_key}
        payload = {
            "sync_tag": sync_tag,
            "fact_sources": self.fact_sources,
            "metrics": self.metrics
        }
        payload = self._attach_reference_url(payload)

        response = requests.post(f'{API_ENDPOINT}{"?allow_upgrades=true" if self.allow_upgrades else ""}', json=payload, headers=headers)

        if response.status_code < 400:
            print('Metrics synced')
        else:
            raise Exception(f"Request failed {response.status_code}: {response.text}")

        return response
