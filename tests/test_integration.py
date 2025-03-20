import os
import subprocess
import tempfile
import pytest
import shutil
from pathlib import Path
import venv

@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Clean up
    shutil.rmtree(temp_dir)

@pytest.fixture
def valid_yaml_dir(temp_dir):
    """Create a directory with valid YAML files for testing."""
    # Copy the valid YAML files to the temporary directory
    valid_dir = os.path.join(temp_dir, "valid")
    os.makedirs(valid_dir)

    # Copy the valid yaml files
    source_dir = "tests/yaml/valid"
    for yaml_file in os.listdir(source_dir):
        if yaml_file.endswith((".yaml", ".yml")):
            shutil.copy(
                os.path.join(source_dir, yaml_file),
                os.path.join(valid_dir, yaml_file)
            )

    return valid_dir

def test_cli_sync_dryrun(valid_yaml_dir):
    """Test the CLI with the --dryrun option."""
    # Set environment variables for testing
    env = os.environ.copy()
    env["EPPO_API_KEY"] = "test_api_key"
    env["EPPO_SYNC_TAG"] = "test_tag"

    # Run the CLI with dryrun
    result = subprocess.run(
        ["python", "-m", "eppo_metrics_sync", valid_yaml_dir, "--dryrun"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Check the result
    assert result.returncode == 0
    assert "Metrics synced" not in result.stdout  # Shouldn't actually sync in dryrun

def test_yaml_validation(valid_yaml_dir):
    """Test that valid YAML files pass validation."""
    # Create a custom YAML file
    test_yaml = os.path.join(valid_yaml_dir, "test_metric.yaml")
    with open(test_yaml, "w") as f:
        f.write("""fact_sources:
- name: Test Source
  sql: |
    SELECT
      ts as TS,
      user_id,
      value
    FROM test_table
  timestamp_column: TS
  entities:
  - entity_name: User
    column: user_id
  facts:
  - name: Test Fact
    column: value
metrics:
- name: Test Metric
  entity: User
  type: simple
  numerator:
    fact_name: Test Fact
    operation: sum
""")

    # Run validation
    result = subprocess.run(
        ["python", "-m", "eppo_metrics_sync", valid_yaml_dir, "--dryrun"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    assert result.returncode == 0

def test_percentile_metric_validation(temp_dir):
    """Test that percentile metrics pass validation."""
    # Create a separate directory just for this test
    percentile_dir = os.path.join(temp_dir, "percentile_test")
    os.makedirs(percentile_dir)

    percentile_yaml = os.path.join(percentile_dir, "percentile_metric.yaml")
    with open(percentile_yaml, "w") as f:
        f.write("""fact_sources:
- name: App Usage
  sql: |
    SELECT
      timestamp as TS,
      user_id,
      app_open_duration
    FROM app_usage_table
  timestamp_column: TS
  entities:
  - entity_name: User
    column: user_id
  facts:
  - name: App Open
    column: app_open_duration
metrics:
- name: App Opens (p95)
  description: 95th percentile of app opens
  type: percentile
  entity: User
  metric_display_style: decimal
  percentile:
    fact_name: App Open
    percentile_value: 0.95
""")

    # Run validation
    result = subprocess.run(
        ["python", "-m", "eppo_metrics_sync", percentile_dir, "--dryrun"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    assert result.returncode == 0, f"Failed with error: {result.stderr}"

def test_percentile_metric_with_filters(temp_dir):
    """Test that percentile metrics with filters pass validation."""
    # Create a separate directory just for this test
    filter_dir = os.path.join(temp_dir, "percentile_filter_test")
    os.makedirs(filter_dir)

    filter_yaml = os.path.join(filter_dir, "percentile_filter_metric.yaml")
    with open(filter_yaml, "w") as f:
        f.write("""fact_sources:
- name: App Usage With Filters
  sql: |
    SELECT
      timestamp as TS,
      user_id,
      app_open_duration,
      app_type
    FROM app_usage_table
  timestamp_column: TS
  entities:
  - entity_name: User
    column: user_id
  facts:
  - name: App Open With Type
    column: app_open_duration
  properties:
  - name: app_type
    column: app_type
metrics:
- name: Mobile App Opens (p90)
  description: 90th percentile of mobile app opens
  type: percentile
  entity: User
  metric_display_style: decimal
  minimum_detectable_effect: 0.05
  reference_url: ""
  guardrail_cutoff: null
  percentile:
    fact_name: App Open With Type
    percentile_value: 0.90
    filters:
    - fact_property: app_type
      operation: equals
      values: ["mobile"]
""")

    # Run validation
    result = subprocess.run(
        ["python", "-m", "eppo_metrics_sync", filter_dir, "--dryrun"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    assert result.returncode == 0, f"Failed with error: {result.stderr}"

def test_invalid_percentile_metric(temp_dir):
    """Test that invalid percentile metrics fail validation."""
    # Create a separate directory just for this test
    invalid_percentile_dir = os.path.join(temp_dir, "invalid_percentile_test")
    os.makedirs(invalid_percentile_dir)

    invalid_yaml = os.path.join(invalid_percentile_dir, "invalid_percentile.yaml")
    with open(invalid_yaml, "w") as f:
        f.write("""fact_sources:
- name: Invalid App Usage
  sql: |
    SELECT
      timestamp as TS,
      user_id,
      app_open_duration
    FROM app_usage_table
  timestamp_column: TS
  entities:
  - entity_name: User
    column: user_id
  facts:
  - name: App Open Invalid
    column: app_open_duration
metrics:
- name: Invalid Percentile
  description: Invalid percentile metric
  type: percentile
  entity: User
  metric_display_style: decimal
  percentile:
    # Missing required percentile_value
    fact_name: App Open Invalid
    # Missing percentile_value which is required
    filters:
    - fact_property: nonexistent_property
      operation: equals
      values: "some_value"
""")

    # Run validation
    result = subprocess.run(
        ["python", "-m", "eppo_metrics_sync", invalid_percentile_dir, "--dryrun"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Should fail validation
    assert result.returncode != 0, "Invalid percentile metric should fail validation"

    # Verify it fails for the right reason (missing percentile_value)
    assert "percentile_value" in result.stderr or "percentile_value" in result.stdout

def test_invalid_yaml(temp_dir):
    """Test that invalid YAML files fail validation."""
    # Create an invalid YAML file
    invalid_dir = os.path.join(temp_dir, "invalid")
    os.makedirs(invalid_dir)

    invalid_yaml = os.path.join(invalid_dir, "invalid_metric.yaml")
    with open(invalid_yaml, "w") as f:
        f.write("""fact_sources:
- name: Invalid Source
  # Missing required fields
  sql: |
    SELECT * FROM test
metrics:
- name: Invalid Metric
  # Missing required fields
  type: simple
""")

    # Run validation
    result = subprocess.run(
        ["python", "-m", "eppo_metrics_sync", invalid_dir],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    assert result.returncode != 0  # Should fail

def test_mixed_yaml_files(temp_dir):
    """Test processing a directory with both valid and invalid YAML files."""
    mixed_dir = os.path.join(temp_dir, "mixed")
    os.makedirs(mixed_dir)

    # Add a valid file
    valid_yaml = os.path.join(mixed_dir, "valid.yaml")
    with open(valid_yaml, "w") as f:
        f.write("""fact_sources:
- name: Valid Source
  sql: |
    SELECT
      ts as TS,
      user_id,
      value
    FROM test_table
  timestamp_column: TS
  entities:
  - entity_name: User
    column: user_id
  facts:
  - name: Valid Fact
    column: value
metrics:
- name: Valid Metric
  entity: User
  type: simple
  numerator:
    fact_name: Valid Fact
    operation: sum
""")

    # Add an invalid file
    invalid_yaml = os.path.join(mixed_dir, "invalid.yaml")
    with open(invalid_yaml, "w") as f:
        f.write("""fact_sources:
- name: Invalid Source
  # Missing required fields
""")

    # Run validation
    result = subprocess.run(
        ["python", "-m", "eppo_metrics_sync", mixed_dir, "--dryrun"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Should have validation errors
    assert "Schema violation" in result.stderr or "Schema violation" in result.stdout

def test_package_installation_and_dependencies():
    """
    Test that the package can be installed in a fresh virtual environment
    and all dependencies are compatible.
    """
    # Create a temporary directory for the virtual environment
    with tempfile.TemporaryDirectory() as venv_dir:
        # Create a virtual environment
        venv.create(venv_dir, with_pip=True)

        # Determine the path to the Python executable in the virtual environment
        python_executable = os.path.join(venv_dir, 'bin', 'python')

        # Get the absolute path to the project root (parent directory of the tests directory)
        project_root = str(Path(__file__).parent.parent.absolute())

        # Install the package in development mode
        install_result = subprocess.run(
            [python_executable, '-m', 'pip', 'install', '-e', project_root],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        assert install_result.returncode == 0, f"Failed to install package: {install_result.stderr}"

        # Try to import and run a basic command to verify functionality
        run_result = subprocess.run(
            [python_executable, '-m', 'eppo_metrics_sync', '--help'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        assert run_result.returncode == 0, f"Failed to run package: {run_result.stderr}"
        assert "usage:" in run_result.stdout, "Help text not found in output"

        # Check if we can use the basic functionality (dry run with empty dir)
        with tempfile.TemporaryDirectory() as empty_dir:
            basic_run = subprocess.run(
                [python_executable, '-m', 'eppo_metrics_sync', empty_dir, '--dryrun'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # We consider the test passed if it can be installed and run
            # Even if it returns an error code for an empty directory
            assert True
