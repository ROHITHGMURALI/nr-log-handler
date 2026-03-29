import json
import pytest
import requests
from unittest.mock import patch, MagicMock
from newrelic_logger.client import NewRelicClient
from newrelic_logger.exceptions import ConfigurationError


@pytest.fixture
def client():
    return NewRelicClient(api_key="test-key", region="us")


def test_send_posts_to_us_endpoint(client):
    logs = [{"timestamp": 1000, "message": "hello", "level": "INFO", "attributes": {}}]
    with patch("newrelic_logger.client.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=202, ok=True)
        client.send(logs)

    mock_post.assert_called_once()
    url = mock_post.call_args.args[0]
    assert url == "https://log-api.newrelic.com/log/v1"


def test_send_posts_to_eu_endpoint():
    eu_client = NewRelicClient(api_key="test-key", region="eu")
    logs = [{"timestamp": 1000, "message": "hello", "level": "INFO", "attributes": {}}]
    with patch("newrelic_logger.client.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=202, ok=True)
        eu_client.send(logs)

    url = mock_post.call_args.args[0]
    assert url == "https://log-api.eu.newrelic.com/log/v1"


def test_send_sets_api_key_header(client):
    logs = [{"timestamp": 1000, "message": "hello", "level": "INFO", "attributes": {}}]
    with patch("newrelic_logger.client.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=202, ok=True)
        client.send(logs)

    headers = mock_post.call_args.kwargs["headers"]
    assert headers["Api-Key"] == "test-key"
    assert headers["Content-Type"] == "application/json"


def test_send_builds_correct_payload(client):
    logs = [
        {"timestamp": 1711000000000, "message": "test msg", "level": "ERROR", "attributes": {"x": "1"}},
    ]
    with patch("newrelic_logger.client.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=202, ok=True)
        client.send(logs)

    payload = json.loads(mock_post.call_args.kwargs["data"])
    assert payload[0]["logs"][0]["message"] == "test msg"
    assert payload[0]["logs"][0]["level"] == "ERROR"
    assert payload[0]["logs"][0]["timestamp"] == 1711000000000
    assert payload[0]["logs"][0]["attributes"] == {"x": "1"}


def test_send_includes_common_attributes_in_payload(client):
    logs = [{"timestamp": 1000, "message": "test", "level": "INFO", "attributes": {}}]
    with patch("newrelic_logger.client.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=202, ok=True)
        client.send(logs, common_attributes={"service": "svc", "env": "prod"})

    payload = json.loads(mock_post.call_args.kwargs["data"])
    assert payload[0]["common"]["attributes"]["service"] == "svc"
    assert payload[0]["common"]["attributes"]["env"] == "prod"
    assert payload[0]["logs"][0]["message"] == "test"


def test_send_without_common_attributes_omits_common_block(client):
    logs = [{"timestamp": 1000, "message": "test", "level": "INFO", "attributes": {}}]
    with patch("newrelic_logger.client.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=202, ok=True)
        client.send(logs)

    payload = json.loads(mock_post.call_args.kwargs["data"])
    assert "common" not in payload[0]


def test_raises_on_invalid_region():
    with pytest.raises(ConfigurationError, match="region"):
        NewRelicClient(api_key="key", region="ap")


def test_raises_on_empty_api_key():
    with pytest.raises(ConfigurationError, match="api_key"):
        NewRelicClient(api_key="")


def test_retries_on_429(client):
    logs = [{"timestamp": 1000, "message": "x", "level": "INFO", "attributes": {}}]
    responses = [MagicMock(status_code=429, ok=False, text="rate limit")] * 5 + [
        MagicMock(status_code=202, ok=True)
    ]
    with patch("newrelic_logger.client.requests.post", side_effect=responses) as mock_post:
        with patch("newrelic_logger.client.time.sleep"):
            client.send(logs)
    assert mock_post.call_count == 6


def test_retries_on_500(client):
    logs = [{"timestamp": 1000, "message": "x", "level": "INFO", "attributes": {}}]
    responses = [MagicMock(status_code=500, ok=False, text="err")] * 5 + [
        MagicMock(status_code=202, ok=True)
    ]
    with patch("newrelic_logger.client.requests.post", side_effect=responses) as mock_post:
        with patch("newrelic_logger.client.time.sleep"):
            client.send(logs)
    assert mock_post.call_count == 6


def test_no_retry_on_400(client):
    logs = [{"timestamp": 1000, "message": "x", "level": "INFO", "attributes": {}}]
    with patch("newrelic_logger.client.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=400, ok=False, text="bad")
        client.send(logs)
    assert mock_post.call_count == 1


def test_no_retry_on_403(client):
    logs = [{"timestamp": 1000, "message": "x", "level": "INFO", "attributes": {}}]
    with patch("newrelic_logger.client.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=403, ok=False, text="forbidden")
        client.send(logs)
    assert mock_post.call_count == 1


def test_warns_after_exhausting_retries(client, caplog):
    import logging as stdlib_logging
    logs = [{"timestamp": 1000, "message": "x", "level": "INFO", "attributes": {}}]
    with patch("newrelic_logger.client.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=500, ok=False, text="err")
        with patch("newrelic_logger.client.time.sleep"):
            with caplog.at_level(stdlib_logging.WARNING, logger="newrelic_logger"):
                client.send(logs)
    assert "Failed to send" in caplog.text
    assert mock_post.call_count == 6  # 1 initial + 5 retries


def test_retries_on_connection_error(client):
    logs = [{"timestamp": 1000, "message": "x", "level": "INFO", "attributes": {}}]
    with patch("newrelic_logger.client.requests.post") as mock_post:
        mock_post.side_effect = requests.ConnectionError("no connection")
        with patch("newrelic_logger.client.time.sleep"):
            client.send(logs)
    assert mock_post.call_count == 6  # 1 initial + 5 retries
