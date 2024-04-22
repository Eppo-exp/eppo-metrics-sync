import subprocess
import pytest

pytest_plugins = ["pytester"]

@pytest.fixture
def run_cli():
    def runner(args):
        result = subprocess.run(['python3', '-m', 'eppo_metrics_sync', *args], 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE, 
                                text=True)
        return result
    return runner

"""def test_cli_with_valid_directory(run_cli):
    result = run_cli(['tests/yaml/valid'])
    assert result.returncode == 0
"""

def test_cli_dbt_valid_directory(run_cli):
    result = run_cli([
        '--dryrun',
        '--schema=dbt-model', 
        '--dbt-model-prefix=foo',
        'tests/yaml/dbt/valid',
        ])
