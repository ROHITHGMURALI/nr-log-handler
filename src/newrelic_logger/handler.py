from __future__ import annotations

import logging

from newrelic_logger.client import NewRelicClient
from newrelic_logger.batch import BatchQueue
from newrelic_logger.exceptions import ConfigurationError

_VALID_REGIONS = {"us", "eu"}
_VALID_MODES = {"sync", "async"}


class NewRelicHandler(logging.Handler):
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
        level: int = logging.NOTSET,
    ) -> None:
        if not api_key:
            raise ConfigurationError("api_key is required and must not be empty.")
        if region not in _VALID_REGIONS:
            raise ConfigurationError(f"Invalid region '{region}'. Must be one of: {_VALID_REGIONS}")
        if mode not in _VALID_MODES:
            raise ConfigurationError(f"Invalid mode '{mode}'. Must be one of: {_VALID_MODES}")

        super().__init__(level)
        self._global_attributes: dict = attributes or {}
        self._mode = mode
        self._client = NewRelicClient(
            api_key=api_key,
            region=region,
            timeout=timeout,
            max_retries=max_retries,
            backoff_factor=backoff_factor,
        )
        self._batch_queue: BatchQueue | None = None
        if mode == "async":
            self._batch_queue = BatchQueue(
                client=self._client,
                batch_size=batch_size,
                flush_interval=flush_interval,
                common_attributes=self._global_attributes or None,
            )

    def emit(self, record: logging.LogRecord) -> None:
        try:
            extra_attrs: dict = getattr(record, "extra_attributes", {}) or {}
            log_dict = {
                "timestamp": int(record.created * 1000),
                "message": self.format(record) if self.formatter else record.getMessage(),
                "level": record.levelname,
                "attributes": extra_attrs,
            }
            if self._mode == "async" and self._batch_queue is not None:
                self._batch_queue.put(log_dict)
            else:
                self._client.send([log_dict], common_attributes=self._global_attributes or None)
        except Exception:
            self.handleError(record)

    def close(self) -> None:
        if self._batch_queue is not None:
            self._batch_queue.close()
        super().close()
