import logging
import pytest
from unittest.mock import MagicMock
from newrelic_logger.logger import NewRelicLogger
from newrelic_logger.exceptions import ConfigurationError


def make_logger(**kwargs) -> NewRelicLogger:
    logger = NewRelicLogger(api_key="test-key", **kwargs)
    logger._handler._client = MagicMock()
    return logger


def test_raises_if_no_api_key():
    with pytest.raises(ConfigurationError):
        NewRelicLogger(api_key="")


def test_info_sends_info_level():
    logger = make_logger()
    logger.info("info message")
    sent = logger._handler._client.send.call_args[0][0]
    assert sent[0]["level"] == "INFO"
    assert sent[0]["message"] == "info message"


def test_debug_sends_debug_level():
    logger = make_logger()
    logger.debug("debug message")
    sent = logger._handler._client.send.call_args[0][0]
    assert sent[0]["level"] == "DEBUG"


def test_warning_sends_warning_level():
    logger = make_logger()
    logger.warning("warn message")
    sent = logger._handler._client.send.call_args[0][0]
    assert sent[0]["level"] == "WARNING"


def test_error_sends_error_level():
    logger = make_logger()
    logger.error("error message")
    sent = logger._handler._client.send.call_args[0][0]
    assert sent[0]["level"] == "ERROR"


def test_critical_sends_critical_level():
    logger = make_logger()
    logger.critical("critical message")
    sent = logger._handler._client.send.call_args[0][0]
    assert sent[0]["level"] == "CRITICAL"


def test_extra_attributes_passed_through():
    logger = make_logger(attributes={"service": "svc"})
    logger.info("msg", extra_attributes={"req_id": "xyz"})
    call_kwargs = logger._handler._client.send.call_args.kwargs
    sent = logger._handler._client.send.call_args[0][0]
    # global attr in common_attributes
    assert call_kwargs["common_attributes"]["service"] == "svc"
    # per-call attr in log entry attributes
    assert sent[0]["attributes"]["req_id"] == "xyz"


def test_close_flushes_handler():
    logger = make_logger(mode="async")
    logger._handler._batch_queue = MagicMock()
    logger.close()
    logger._handler._batch_queue.close.assert_called_once()
