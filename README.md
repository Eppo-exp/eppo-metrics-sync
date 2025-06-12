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

export EPPO_REFERENCE_URL="your-reference-url" # optional
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
-   `--allow-upgrades` Allow existing non-certified metrics/fact sources to become certified

#### When to use `--allow-upgrades`

The `--allow-upgrades` flag is useful in the following scenarios:

-   **Promoting existing metrics to certified status**: If you have existing metrics or fact sources in Eppo that are not currently certified, this flag allows them to be upgraded to certified status during the sync process.
-   **Migrating from manual to code-managed metrics**: When transitioning from manually created metrics in the Eppo UI to managing them through YAML files, this flag enables the promotion of those metrics to certified status.
-   **Avoiding conflicts during migration**: Without this flag, attempting to sync metrics that already exist in a non-certified state may result in conflicts or the sync process not upgrading their certification status.

## Validation Rules & Constraints

The following validation rules are enforced when syncing metrics. Understanding these constraints upfront can help avoid validation errors during development:

### Winsorization Constraints

Winsorization parameters (`winsorization_lower_percentile`, `winsorization_upper_percentile`) can **only** be used with these aggregation operations:
- ✅ `sum`
- ✅ `count` 
- ✅ `last_value`
- ✅ `first_value`

**Not supported for:**
- ❌ `count_distinct` - Use different outlier handling approaches
- ❌ `distinct_entity` - Binary metrics don't need winsorization
- ❌ `threshold` - Threshold logic handles outliers differently
- ❌ `retention` - Binary retention metrics don't need winsorization  
- ❌ `conversion` - Binary conversion metrics don't need winsorization

### Advanced Aggregation Parameters

Each advanced aggregation type requires its specific parameter and cannot use others:

#### Threshold Metrics
- **Required**: `threshold_metric_settings` object with:
  - `comparison_operator`: "gt" or "gte"
  - `aggregation_type`: "sum" or "count" (**not** count_distinct)
  - `breach_value`: numeric threshold value
- **Cannot use**: `retention_threshold_days`, `conversion_threshold_days`

#### Retention Metrics  
- **Required**: `retention_threshold_days` (numeric)
- **Cannot use**: `threshold_metric_settings`, `conversion_threshold_days`

#### Conversion Metrics
- **Required**: `conversion_threshold_days` (numeric)  
- **Cannot use**: `threshold_metric_settings`, `retention_threshold_days`
- **Cannot use**: Timeframe parameters (`aggregation_timeframe_start_value`, `aggregation_timeframe_end_value`)

### Timeframe Parameters

When using aggregation timeframe parameters:
- **Required**: `aggregation_timeframe_unit` must be specified if any timeframe parameters are used
- **Supported units**: "minutes", "hours", "days", "weeks", "calendar_days"
- **Not supported for**: `conversion` operations (use `conversion_threshold_days` instead)

### Denominator Constraints

For ratio metrics, denominators can only use these operations:
- ✅ `sum`, `count`, `count_distinct`, `distinct_entity`, `last_value`, `first_value`
- ❌ Cannot use: `threshold`, `retention`, `conversion`

### Guardrail Cutoff Signs

When using guardrail metrics (`is_guardrail: true` with `guardrail_cutoff`):
- If fact's `desired_change: "increase"` → `guardrail_cutoff` must be **negative**
- If fact's `desired_change: "decrease"` → `guardrail_cutoff` must be **positive**

## Documentation

For detailed information about metric configuration, available options and constraints, see Eppo's [documentation page](https://docs.geteppo.com/data-management/certified-metrics/).

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

### Running the package

```bash
export EPPO_API_KEY="your-api-key"
export EPPO_SYNC_TAG="your-sync-tag"
export EPPO_REFERENCE_URL="your-reference-url"
python -m eppo_metrics_sync path/to/yaml/directory
```

### Building and Publishing

For package maintainers:

1. Update version in `pyproject.toml`
2. Build the package:

```bash
python -m build
```

3. The package will be automatically published to PyPI when a new release is created on GitHub.
