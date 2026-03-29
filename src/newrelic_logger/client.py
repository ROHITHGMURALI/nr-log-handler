from __future__ import annotations

import json
import logging
import time

import requests

from newrelic_logger.exceptions import ConfigurationError

_ENDPOINTS: dict[str, str] = {
    "us": "https://log-api.newrelic.com/log/v1",
    "eu": "https://log-api.eu.newrelic.com/log/v1",
}

_internal_logger = logging.getLogger("newrelic_logger")


class NewRelicClient:
    def __init__(
        self,
        api_key: str,
        region: str = "us",
        timeout: int = 10,
        max_retries: int = 5,
        backoff_factor: float = 0.5,
    ) -> None:
        if not api_key:
            raise ConfigurationError("api_key is required and must not be empty.")
        if region not in _ENDPOINTS:
            raise ConfigurationError(f"Invalid region '{region}'. Must be one of: {set(_ENDPOINTS)}")
        self._api_key = api_key
        self._endpoint = _ENDPOINTS[region]
        self._timeout = timeout
        self._max_retries = max_retries
        self._backoff_factor = backoff_factor

    def send(self, logs: list[dict], common_attributes: dict | None = None) -> None:
        entry: dict = {"logs": logs}
        if common_attributes:
            entry["common"] = {"attributes": common_attributes}
        payload = json.dumps([entry])
        headers = {
            "Api-Key": self._api_key,
            "Content-Type": "application/json",
        }
        self._post_with_retry(payload, headers, logs)

    def _post_with_retry(self, payload: str, headers: dict, logs: list[dict]) -> None:
        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            if attempt > 0:
                wait = self._backoff_factor * (2 ** (attempt - 1))
                time.sleep(wait)
            try:
                response = requests.post(
                    self._endpoint, data=payload, headers=headers, timeout=self._timeout
                )
                if response.ok:
                    return
                if response.status_code in (400, 403):
                    _internal_logger.warning(
                        "newrelic_logger: Permanent failure sending %d log(s) — HTTP %d: %s",
                        len(logs),
                        response.status_code,
                        response.text,
                    )
                    return
                last_exc = RuntimeError(f"HTTP {response.status_code}: {response.text}")
            except requests.RequestException as exc:
                last_exc = exc

        _internal_logger.warning(
            "newrelic_logger: Failed to send %d log(s) to New Relic after %d retries: %s",
            len(logs),
            self._max_retries,
            str(last_exc),
        )
