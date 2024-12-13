# Eppo Metrics Sync

[![PyPI version](https://badge.fury.io/py/eppo-metrics-sync.svg)](https://badge.fury.io/py/eppo-metrics-sync)
[![Tests](https://github.com/Eppo-exp/eppo-metrics-sync/actions/workflows/run_tests.yml/badge.svg)](https://github.com/Eppo-exp/eppo-metrics-sync/actions)

A Python package for syncing metric definitions with Eppo's API. Manage your Eppo metrics as code using YAML files. Documentation is available in Eppo's [documentation page](https://docs.geteppo.com/data-management/certified-metrics/).

## Features

-   Sync metrics and fact sources to Eppo
-   Validate metric definitions locally
-   Support for dbt models
-   Dry-run capability for testing
-   Prefix support for testing in shared workspaces

## Installation

```bash
pip install eppo-metrics-sync
```

## Usage

### Basic usage

1. Set required environment variables:

```bash
export EPPO_API_KEY="your-api-key"

export EPPO_SYNC_TAG="your-sync-tag" # optional
```

2. Create your metrics YAML files (see [Documentation](#documentation))

3. Run the sync:

```bash
python -m eppo_metrics_sync path/to/yaml/directory
```

### CLI Options

```bash
python -m eppo_metrics_sync [OPTIONS] DIRECTORY
```

Options:

-   `--dryrun` Validate files without syncing to Eppo
-   `--schema` Schema type: eppo (default) or dbt-model
-   `--sync-prefix` Prefix for fact/metric names (useful for testing)
-   `--dbt-model-prefix` Warehouse/schema prefix for dbt models

## Documentation

For detailed information about metric configuration and available options, see Eppo's [documentation page](https://docs.geteppo.com/data-management/certified-metrics/).

### Example YAML Configuration

```yaml
fact_sources:
    - name: Revenue
      sql: |
          SELECT ts, user_id, amount
          FROM revenue_table
      timestamp_column: ts
      entities:
          - entity_name: User
            column: user_id
      facts:
          - name: Revenue
            column: amount

metrics:
    - name: Total Revenue
      description: Sum of Total Purchase Value in Purchases Fact Table
      entity: User
      numerator:
          fact_name: Revenue
          operation: sum
```

## Development

### Setup

#### Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

#### Install dependencies

```bash
pip install -r requirements.txt
```

### Running the tests

```bash
pytest tests
```

### Building and Publishing

For package maintainers:

1. Update version in `pyproject.toml`
2. Build the package:

```bash
python -m build
```

3. The package will be automatically published to PyPI when a new release is created on GitHub.
