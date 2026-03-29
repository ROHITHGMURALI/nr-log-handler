import logging
import pytest
from unittest.mock import MagicMock, patch
from newrelic_logger.handler import NewRelicHandler
from newrelic_logger.exceptions import ConfigurationError


def test_raises_if_no_api_key():
    with pytest.raises(ConfigurationError, match="api_key"):
        NewRelicHandler(api_key="")


def test_raises_on_invalid_region():
    with pytest.raises(ConfigurationError, match="region"):
        NewRelicHandler(api_key="key", region="ap")


def test_raises_on_invalid_mode():
    with pytest.raises(ConfigurationError, match="mode"):
        NewRelicHandler(api_key="key", mode="streaming")


def test_sync_mode_calls_client_send():
    handler = NewRelicHandler(api_key="key", mode="sync")
    handler._client = MagicMock()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="hello world", args=(), exc_info=None,
    )
    handler.emit(record)
    handler._client.send.assert_called_once()
    sent = handler._client.send.call_args[0][0]
    assert sent[0]["message"] == "hello world"
    assert sent[0]["level"] == "INFO"


def test_async_mode_puts_to_batch_queue():
    handler = NewRelicHandler(api_key="key", mode="async")
    handler._batch_queue = MagicMock()
    record = logging.LogRecord(
        name="test", level=logging.ERROR, pathname="", lineno=0,
        msg="async log", args=(), exc_info=None,
    )
    handler.emit(record)
    handler._batch_queue.put.assert_called_once()
    sent = handler._batch_queue.put.call_args[0][0]
    assert sent["message"] == "async log"
    assert sent["level"] == "ERROR"


def test_global_attributes_merged():
    handler = NewRelicHandler(api_key="key", mode="sync", attributes={"service": "svc"})
    handler._client = MagicMock()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="msg", args=(), exc_info=None,
    )
    handler.emit(record)
    # Global attrs now passed as common_attributes keyword arg
    call_kwargs = handler._client.send.call_args.kwargs
    assert call_kwargs["common_attributes"]["service"] == "svc"


def test_per_call_attributes_override_global():
    handler = NewRelicHandler(api_key="key", mode="sync", attributes={"env": "prod"})
    handler._client = MagicMock()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="msg", args=(), exc_info=None,
    )
    record.extra_attributes = {"env": "staging", "req_id": "abc"}
    handler.emit(record)
    sent = handler._client.send.call_args[0][0]
    call_kwargs = handler._client.send.call_args.kwargs
    # per-call attrs in the log entry itself
    assert sent[0]["attributes"]["env"] == "staging"
    assert sent[0]["attributes"]["req_id"] == "abc"
    # global attrs still in common_attributes
    assert call_kwargs["common_attributes"]["env"] == "prod"


def test_close_calls_batch_queue_close():
    handler = NewRelicHandler(api_key="key", mode="async")
    handler._batch_queue = MagicMock()
    handler.close()
    handler._batch_queue.close.assert_called_once()
