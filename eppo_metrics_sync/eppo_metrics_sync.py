import json
import jsonschema
import math
import os
import requests
import time

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
ASYNC_API_ENDPOINT = f'{API_ENDPOINT}/async'

DEFAULT_POLL_INTERVAL = 5
DEFAULT_POLL_TIMEOUT = 600


def _resolve_poll_setting(value, env_var, default):
    """
    Poll settings can be passed explicitly, set in the environment, or left
    to the package default, in that order of precedence.
    """

    if value is None:
        value = os.getenv(env_var)

    if value is None:
        return default

    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValueError(f'{env_var} must be a number, got: {value}')

    if not math.isfinite(value):
        raise ValueError(f'{env_var} must be finite, got: {value}')

    if value < 0:
        raise ValueError(f'{env_var} must not be negative, got: {value}')

    # keep whole numbers as ints so they read cleanly in log messages
    return int(value) if value.is_integer() else value


class EppoMetricsSync:
    def __init__(
            self,
            directory,
            schema_type='eppo',
            dbt_model_prefix=None,
            sync_prefix=None,
            allow_upgrades=False,
            poll_interval=None,
            poll_timeout=None
    ):
        self.directory = directory
        self.fact_sources = []
        self.metrics = []
        self.validation_errors = []
        self.schema_type = schema_type
        self.dbt_model_prefix = dbt_model_prefix
        self.sync_prefix = sync_prefix
        self.allow_upgrades = allow_upgrades
        self.poll_interval = _resolve_poll_setting(
            poll_interval, 'EPPO_SYNC_POLL_INTERVAL', DEFAULT_POLL_INTERVAL
        )
        self.poll_timeout = _resolve_poll_setting(
            poll_timeout, 'EPPO_SYNC_POLL_TIMEOUT', DEFAULT_POLL_TIMEOUT
        )

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

    def _start_async_sync(self, payload, headers):
        """
        Kick off an asynchronous sync and return the initial sync status
        """

        url = ASYNC_API_ENDPOINT
        if self.allow_upgrades:
            url += '?allow_upgrades=true'

        response = requests.post(url, json=payload, headers=headers)

        # Eppo returns 304 with no status body when the payload is identical to
        # the last successful sync for this sync tag, meaning there is nothing
        # to enqueue and nothing to poll for
        if response.status_code == 304:
            return {
                'sync_tag': payload.get('sync_tag'),
                'status': 'success',
                'unchanged': True
            }

        if response.status_code >= 400:
            raise Exception(f"Request failed {response.status_code}: {response.text}")

        return self._parse_sync_status(response)

    def _get_sync_status(self, sync_id, headers, timeout):
        """
        Fetch the current status of an in-flight sync
        """

        response = requests.get(
            f'{API_ENDPOINT}/{sync_id}',
            headers=headers,
            timeout=timeout
        )

        if response.status_code >= 400:
            raise Exception(
                f"Failed to fetch status for sync {sync_id} "
                f"({response.status_code}): {response.text}"
            )

        return self._parse_sync_status(response)

    @staticmethod
    def _parse_sync_status(response):
        try:
            sync_status = response.json()
        except ValueError:
            raise Exception(f"Unexpected response from Eppo API: {response.text}")

        if not isinstance(sync_status, dict) or 'status' not in sync_status:
            raise Exception(f"Unexpected response from Eppo API: {response.text}")

        return sync_status

    @staticmethod
    def _sync_failure_message(sync_status):
        message = f"Metrics sync {sync_status.get('id')} failed"
        errors = sync_status.get('errors')
        if errors:
            message += ': \n' + '\n'.join(str(error) for error in errors)

        return message

    def _poll_timeout_message(self, sync_id):
        return (
            f"Timed out after {self.poll_timeout} seconds waiting for "
            f"metrics sync {sync_id} to complete. The sync may still be "
            f"running in Eppo."
        )

    def _wait_for_sync(self, sync_id, headers, initial_status=None):
        """
        Poll the sync status endpoint until the sync reaches a terminal state,
        or until poll_timeout seconds have elapsed
        """

        deadline = time.monotonic() + self.poll_timeout
        sync_status = initial_status

        while True:
            if sync_status is None:
                time_remaining = deadline - time.monotonic()
                if time_remaining <= 0:
                    raise Exception(self._poll_timeout_message(sync_id))

                try:
                    sync_status = self._get_sync_status(
                        sync_id,
                        headers,
                        timeout=time_remaining
                    )
                except requests.Timeout as error:
                    raise Exception(self._poll_timeout_message(sync_id)) from error

                if time.monotonic() >= deadline:
                    raise Exception(self._poll_timeout_message(sync_id))

            status = sync_status.get('status')

            if status == 'success':
                print(f'Metrics synced (sync id: {sync_id})')
                return sync_status

            if status == 'failed':
                raise Exception(self._sync_failure_message(sync_status))

            if status != 'pending':
                raise Exception(
                    f"Unexpected status for sync {sync_id}: {status}"
                )

            time_remaining = deadline - time.monotonic()
            if time_remaining <= 0:
                raise Exception(self._poll_timeout_message(sync_id))

            time.sleep(min(self.poll_interval, time_remaining))
            sync_status = None

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

        sync_status = self._start_async_sync(payload, headers)

        if sync_status.get('unchanged'):
            print('Metrics are unchanged since the last successful sync, nothing to do')
            return sync_status

        sync_id = sync_status.get('id')
        if sync_id is None:
            raise Exception(
                f"Eppo API did not return a sync id: {json.dumps(sync_status)}"
            )

        print(f'Metrics sync {sync_id} submitted, waiting for it to complete')

        return self._wait_for_sync(sync_id, headers, initial_status=sync_status)
