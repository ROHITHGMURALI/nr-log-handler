class NewRelicLoggerError(Exception):
    """Base exception for newrelic-logger."""


class ConfigurationError(NewRelicLoggerError):
    """Raised when the handler/logger is misconfigured at init time."""
