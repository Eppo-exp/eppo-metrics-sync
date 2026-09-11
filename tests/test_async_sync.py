import os
import json
import pytest

from unittest import mock

from eppo_metrics_sync.eppo_metrics_sync import (
    EppoMetricsSync,
    API_ENDPOINT,
    ASYNC_API_ENDPOINT,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_POLL_TIMEOUT,
)

VALID_YAML_DIR = os.path.join(os.path.dirname(__file__), 'yaml', 'valid')


class FakeResponse:
    def __init__(self, status_code, body=None, text=None):
        self.status_code = status_code
        self._body = body
        self.text = text if text is not None else json.dumps(body)

    def json(self):
        if self._body is None:
            raise ValueError('No JSON object could be decoded')
        return self._body


@pytest.fixture
def eppo_env(monkeypatch):
    monkeypatch.setenv('EPPO_API_KEY', 'test_api_key')
    monkeypatch.setenv('EPPO_SYNC_TAG', 'test_tag')
    monkeypatch.delenv('EPPO_REFERENCE_URL', raising=False)
    monkeypatch.delenv('EPPO_SYNC_POLL_INTERVAL', raising=False)
    monkeypatch.delenv('EPPO_SYNC_POLL_TIMEOUT', raising=False)


@pytest.fixture
def no_sleep(monkeypatch):
    """Keep the polling tests fast"""
    sleeps = []
    monkeypatch.setattr(
        'eppo_metrics_sync.eppo_metrics_sync.time.sleep', sleeps.append
    )
    return sleeps


def make_sync(**kwargs):
    return EppoMetricsSync(directory=VALID_YAML_DIR, **kwargs)


def test_sync_posts_to_async_endpoint_and_polls_until_success(eppo_env, no_sleep):
    post = mock.Mock(return_value=FakeResponse(
        202, {'id': 42, 'sync_tag': 'test_tag', 'status': 'pending'}
    ))
    get = mock.Mock(side_effect=[
        FakeResponse(200, {'id': 42, 'sync_tag': 'test_tag', 'status': 'pending'}),
        FakeResponse(200, {'id': 42, 'sync_tag': 'test_tag', 'status': 'success'}),
    ])

    with mock.patch('eppo_metrics_sync.eppo_metrics_sync.requests.post', post), \
            mock.patch('eppo_metrics_sync.eppo_metrics_sync.requests.get', get):
        result = make_sync(poll_interval=0.01).sync()

    assert result['status'] == 'success'
    assert result['id'] == 42

    post_url, post_kwargs = post.call_args[0][0], post.call_args[1]
    assert post_url == ASYNC_API_ENDPOINT
    assert post_kwargs['headers'] == {'X-Eppo-Token': 'test_api_key'}
    assert post_kwargs['json']['sync_tag'] == 'test_tag'
    assert post_kwargs['json']['fact_sources']
    assert post_kwargs['json']['metrics']

    assert get.call_count == 2
    for call in get.call_args_list:
        assert call[0][0] == f'{API_ENDPOINT}/42'
        assert call[1]['headers'] == {'X-Eppo-Token': 'test_api_key'}

    # slept after the pending 202 and after the pending status check,
    # but not after the terminal one
    assert no_sleep == [0.01, 0.01]


def test_sync_returns_immediately_when_initial_response_is_terminal(eppo_env, no_sleep):
    post = mock.Mock(return_value=FakeResponse(
        202, {'id': 7, 'sync_tag': 'test_tag', 'status': 'success'}
    ))
    get = mock.Mock()

    with mock.patch('eppo_metrics_sync.eppo_metrics_sync.requests.post', post), \
            mock.patch('eppo_metrics_sync.eppo_metrics_sync.requests.get', get):
        result = make_sync().sync()

    assert result['status'] == 'success'
    get.assert_not_called()
    assert no_sleep == []


def test_unchanged_payload_is_a_no_op_success(eppo_env, no_sleep):
    """
    Eppo answers 304 with no status body when the payload matches the last
    successful sync, so there is nothing to poll for
    """

    post = mock.Mock(return_value=FakeResponse(304, text=''))
    get = mock.Mock()

    with mock.patch('eppo_metrics_sync.eppo_metrics_sync.requests.post', post), \
            mock.patch('eppo_metrics_sync.eppo_metrics_sync.requests.get', get):
        result = make_sync().sync()

    assert result['status'] == 'success'
    assert result['unchanged'] is True
    assert result['sync_tag'] == 'test_tag'
    get.assert_not_called()
    assert no_sleep == []


def test_allow_upgrades_adds_query_param(eppo_env, no_sleep):
    post = mock.Mock(return_value=FakeResponse(
        202, {'id': 1, 'sync_tag': 'test_tag', 'status': 'success'}
    ))

    with mock.patch('eppo_metrics_sync.eppo_metrics_sync.requests.post', post):
        make_sync(allow_upgrades=True).sync()

    assert post.call_args[0][0] == f'{ASYNC_API_ENDPOINT}?allow_upgrades=true'


def test_failed_sync_raises_with_errors(eppo_env, no_sleep):
    post = mock.Mock(return_value=FakeResponse(
        202, {'id': 9, 'sync_tag': 'test_tag', 'status': 'pending'}
    ))
    get = mock.Mock(return_value=FakeResponse(200, {
        'id': 9,
        'sync_tag': 'test_tag',
        'status': 'failed',
        'errors': ['Fact source Revenue is invalid', 'Metric foo not found'],
    }))

    with mock.patch('eppo_metrics_sync.eppo_metrics_sync.requests.post', post), \
            mock.patch('eppo_metrics_sync.eppo_metrics_sync.requests.get', get):
        with pytest.raises(Exception) as exc_info:
            make_sync(poll_interval=0).sync()

    message = str(exc_info.value)
    assert 'Metrics sync 9 failed' in message
    assert 'Fact source Revenue is invalid' in message
    assert 'Metric foo not found' in message


def test_poll_timeout_raises(eppo_env, no_sleep):
    post = mock.Mock(return_value=FakeResponse(
        202, {'id': 3, 'sync_tag': 'test_tag', 'status': 'pending'}
    ))
    get = mock.Mock(return_value=FakeResponse(
        200, {'id': 3, 'sync_tag': 'test_tag', 'status': 'pending'}
    ))

    with mock.patch('eppo_metrics_sync.eppo_metrics_sync.requests.post', post), \
            mock.patch('eppo_metrics_sync.eppo_metrics_sync.requests.get', get):
        with pytest.raises(Exception, match='Timed out after 0 seconds'):
            make_sync(poll_timeout=0).sync()

    # the initial 202 counts as the first observation, so no status check is needed
    get.assert_not_called()


def test_unexpected_status_raises(eppo_env, no_sleep):
    post = mock.Mock(return_value=FakeResponse(
        202, {'id': 5, 'sync_tag': 'test_tag', 'status': 'confused'}
    ))

    with mock.patch('eppo_metrics_sync.eppo_metrics_sync.requests.post', post):
        with pytest.raises(Exception, match='Unexpected status for sync 5: confused'):
            make_sync().sync()


def test_failed_post_raises(eppo_env, no_sleep):
    post = mock.Mock(return_value=FakeResponse(403, text='Forbidden'))

    with mock.patch('eppo_metrics_sync.eppo_metrics_sync.requests.post', post):
        with pytest.raises(Exception, match='Request failed 403: Forbidden'):
            make_sync().sync()


def test_failed_status_request_raises(eppo_env, no_sleep):
    post = mock.Mock(return_value=FakeResponse(
        202, {'id': 11, 'sync_tag': 'test_tag', 'status': 'pending'}
    ))
    get = mock.Mock(return_value=FakeResponse(500, text='Internal Server Error'))

    with mock.patch('eppo_metrics_sync.eppo_metrics_sync.requests.post', post), \
            mock.patch('eppo_metrics_sync.eppo_metrics_sync.requests.get', get):
        with pytest.raises(Exception, match='Failed to fetch status for sync 11'):
            make_sync(poll_interval=0).sync()


def test_non_json_response_raises(eppo_env, no_sleep):
    post = mock.Mock(return_value=FakeResponse(202, text='<html>gateway</html>'))

    with mock.patch('eppo_metrics_sync.eppo_metrics_sync.requests.post', post):
        with pytest.raises(Exception, match='Unexpected response from Eppo API'):
            make_sync().sync()


def test_response_without_status_raises(eppo_env, no_sleep):
    post = mock.Mock(return_value=FakeResponse(202, {'id': 12}))

    with mock.patch('eppo_metrics_sync.eppo_metrics_sync.requests.post', post):
        with pytest.raises(Exception, match='Unexpected response from Eppo API'):
            make_sync().sync()


def test_response_without_id_raises(eppo_env, no_sleep):
    post = mock.Mock(return_value=FakeResponse(202, {'status': 'pending'}))

    with mock.patch('eppo_metrics_sync.eppo_metrics_sync.requests.post', post):
        with pytest.raises(Exception, match='did not return a sync id'):
            make_sync().sync()


def test_poll_settings_default(eppo_env):
    eppo_sync = make_sync()
    assert eppo_sync.poll_interval == DEFAULT_POLL_INTERVAL
    assert eppo_sync.poll_timeout == DEFAULT_POLL_TIMEOUT


def test_poll_settings_from_environment(eppo_env, monkeypatch):
    monkeypatch.setenv('EPPO_SYNC_POLL_INTERVAL', '2.5')
    monkeypatch.setenv('EPPO_SYNC_POLL_TIMEOUT', '30')

    eppo_sync = make_sync()
    assert eppo_sync.poll_interval == 2.5
    assert eppo_sync.poll_timeout == 30


def test_explicit_poll_settings_override_environment(eppo_env, monkeypatch):
    monkeypatch.setenv('EPPO_SYNC_POLL_INTERVAL', '2.5')
    monkeypatch.setenv('EPPO_SYNC_POLL_TIMEOUT', '30')

    eppo_sync = make_sync(poll_interval=1, poll_timeout=60)
    assert eppo_sync.poll_interval == 1
    assert eppo_sync.poll_timeout == 60


@pytest.mark.parametrize('value', ['not-a-number', '-1'])
def test_invalid_poll_settings_raise(eppo_env, monkeypatch, value):
    monkeypatch.setenv('EPPO_SYNC_POLL_INTERVAL', value)

    with pytest.raises(ValueError, match='EPPO_SYNC_POLL_INTERVAL'):
        make_sync()
