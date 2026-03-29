from __future__ import annotations

import logging
import uuid

from newrelic_logger.handler import NewRelicHandler


class NewRelicLogger:
    def __init__(
        self,
        api_key: str = "",
        region: str = "us",
        mode: str = "sync",
        batch_size: int = 100,
        flush_interval: float = 5.0,
        timeout: int = 10,
        max_retries: int = 5,
        backoff_factor: float = 0.5,
        attributes: dict | None = None,
    ) -> None:
        self._handler = NewRelicHandler(
            api_key=api_key,
            region=region,
            mode=mode,
            batch_size=batch_size,
            flush_interval=flush_interval,
            timeout=timeout,
            max_retries=max_retries,
            backoff_factor=backoff_factor,
            attributes=attributes,
        )
        # Use a unique logger name to avoid collisions between instances
        self._logger = logging.getLogger(f"newrelic_logger.user.{uuid.uuid4().hex}")
        self._logger.addHandler(self._handler)
        self._logger.setLevel(logging.DEBUG)
        self._logger.propagate = False

    def _log(self, level: int, msg: str, extra_attributes: dict | None = None) -> None:
        extra = {"extra_attributes": extra_attributes or {}}
        self._logger.log(level, msg, extra=extra)

    def debug(self, msg: str, extra_attributes: dict | None = None) -> None:
        self._log(logging.DEBUG, msg, extra_attributes)

    def info(self, msg: str, extra_attributes: dict | None = None) -> None:
        self._log(logging.INFO, msg, extra_attributes)

    def warning(self, msg: str, extra_attributes: dict | None = None) -> None:
        self._log(logging.WARNING, msg, extra_attributes)

    def error(self, msg: str, extra_attributes: dict | None = None) -> None:
        self._log(logging.ERROR, msg, extra_attributes)

    def critical(self, msg: str, extra_attributes: dict | None = None) -> None:
        self._log(logging.CRITICAL, msg, extra_attributes)

    def close(self) -> None:
        self._handler.close()
        self._logger.removeHandler(self._handler)
