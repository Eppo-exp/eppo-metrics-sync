import subprocess
import pytest
from unittest.mock import patch, MagicMock

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

def test_cli_dryrun_option(run_cli):
    result = run_cli(['tests/yaml/valid', '--dryrun'])
    assert result.returncode == 0

def test_cli_invalid_directory(run_cli):
    result = run_cli(['tests/yaml/invalid'])
    assert result.returncode != 0


class TestIsCertifiedParam:
    """Tests for the is_certified query parameter (--no-certify flag)."""

    def _make_sync(self, is_certified=True, allow_upgrades=False):
        from eppo_metrics_sync.eppo_metrics_sync import EppoMetricsSync
        return EppoMetricsSync(
            directory='tests/yaml/valid',
            is_certified=is_certified,
            allow_upgrades=allow_upgrades,
        )

    @patch.dict('os.environ', {'EPPO_API_KEY': 'test-key', 'EPPO_SYNC_TAG': 'test-tag'})
    @patch('eppo_metrics_sync.eppo_metrics_sync.requests.post')
    def test_default_does_not_send_is_certified(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)
        syncer = self._make_sync(is_certified=True)
        syncer.sync()
        _, kwargs = mock_post.call_args
        assert 'is_certified' not in kwargs.get('params', {})

    @patch.dict('os.environ', {'EPPO_API_KEY': 'test-key', 'EPPO_SYNC_TAG': 'test-tag'})
    @patch('eppo_metrics_sync.eppo_metrics_sync.requests.post')
    def test_no_certify_sends_is_certified_false(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)
        syncer = self._make_sync(is_certified=False)
        syncer.sync()
        _, kwargs = mock_post.call_args
        assert kwargs['params']['is_certified'] == 'false'

    @patch.dict('os.environ', {'EPPO_API_KEY': 'test-key', 'EPPO_SYNC_TAG': 'test-tag'})
    @patch('eppo_metrics_sync.eppo_metrics_sync.requests.post')
    def test_no_certify_with_allow_upgrades(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)
        syncer = self._make_sync(is_certified=False, allow_upgrades=True)
        syncer.sync()
        _, kwargs = mock_post.call_args
        assert kwargs['params']['is_certified'] == 'false'
        assert kwargs['params']['allow_upgrades'] == 'true'
