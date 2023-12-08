import json, yaml, jsonschema, os, logging, requests

from eppo_metrics_sync.validation import (
    unique_names, 
    valid_fact_references, 
    aggregation_is_valid,
    metric_aggregation_is_valid
)

API_ENDPOINT = 'https://eppo.cloud/api/v1/metrics/sync'

class EppoMetricsSync:
    def __init__(
        self,
        directory
    ):
        self.directory = directory
        self.fact_sources = []
        self.metrics = []
        self.validation_errors = []

        # temporary: ideally would pull this from Eppo API
        package_root = os.path.dirname(os.path.abspath(__file__))
        schema_path = os.path.join(package_root, 'schema', 'eppo_metric_schema.json')
        with open(schema_path) as schema_file:
            self.schema = json.load(schema_file)
    

    def load_yaml(self, path):
        with open(path, 'r') as yaml_file:
            yaml_data = yaml.safe_load(yaml_file)
            if 'fact_sources' in yaml_data:
                self.fact_sources.extend(yaml_data['fact_sources'])
            if 'metrics' in yaml_data:
                self.metrics.extend(yaml_data['metrics'])
        

    def read_yaml_files(self):

        # Validate a single YAML file against the schema
        def yaml_is_valid(yaml_path):
            with open(yaml_path, 'r') as yaml_file:
                data = yaml.safe_load(yaml_file)
                try:
                    jsonschema.validate(data, self.schema)
                    return {"passed": True}
                except jsonschema.exceptions.ValidationError as e:
                    return {"passed": False, "error_message": e}

        # Recursively scan the directory for YAML files and load valid ones
        for root, _, files in os.walk(self.directory):
            for file in files:
                if file.endswith(".yaml") or file.endswith(".yml"):
                    yaml_path = os.path.join(root, file)
                    valid = yaml_is_valid(yaml_path)
                    if valid['passed']:
                        self.load_yaml(yaml_path)
                    else:
                        self.validation_errors.append(
                            f"Schema violation in {yaml_path}: \n{valid.error_message}"
                        )
        
        if len(self.fact_sources) == 0 and len(self.metrics) == 0:
            raise ValueError(
                'No valid yaml files found. ' + ', '.join(self.validation_errors)
            )


    def validate(self):

        if(len(self.fact_sources) == 0 and len(self.metrics) == 0):
            raise ValueError('No fact sources or metrics found, did you call eppo_metrics.read_yaml_files()?')
        
        unique_names(self)
        valid_fact_references(self)
        metric_aggregation_is_valid(self)

        if self.validation_errors:
            error_count = len(self.validation_errors)
            error_message = f"Validation failed with {error_count} error(s): \n"
            error_message += '\n'.join(self.validation_errors)
            raise ValueError(error_message)

        return True


    def sync(self):
        self.read_yaml_files()
        self.validate()

        api_key = os.getenv('EPPO_API_KEY')
        if not api_key:
            raise Exception('EPPO_API_KEY not set in environment variables. Please set and try again')
        
        sync_tag = os.getenv('EPPO_SYNC_TAG')
        if not api_key:
            raise Exception('EPPO_SYNC_TAG not set in environment variables. Please set and try again')
        
        headers = {"X-Eppo-Token": api_key}
        payload = {
            "sync_tag": sync_tag,
            "fact_sources" : self.fact_sources,
            "metrics" : self.metrics
        }

        response = requests.post(API_ENDPOINT, json=payload, headers=headers)

        if response.status_code < 400:
            print('Metrics synced')
        else:
            raise Exception(f"Request failed {response.status_code}: {response.text}")

        return response
