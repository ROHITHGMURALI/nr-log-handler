from newrelic_logger.exceptions import NewRelicLoggerError, ConfigurationError


def test_configuration_error_is_newrelic_logger_error():
    err = ConfigurationError("bad config")
    assert isinstance(err, NewRelicLoggerError)
    assert str(err) == "bad config"


def test_newrelic_logger_error_is_exception():
    err = NewRelicLoggerError("base")
    assert isinstance(err, Exception)
