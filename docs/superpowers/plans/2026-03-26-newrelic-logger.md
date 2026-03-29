# newrelic-logger Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and publish a PyPI-ready Python package that sends logs to New Relic via their Log REST API, supporting sync/async modes, batching, retries, and both standalone and `logging.Handler` usage patterns.

**Architecture:** A `NewRelicClient` handles all HTTP, a `BatchQueue` buffers records in async mode, a `NewRelicHandler` (subclass of `logging.Handler`) owns routing logic, and a `NewRelicLogger` wraps everything into a convenience API. All retry/drop/warn behaviour lives in `NewRelicClient`.

**Tech Stack:** Python 3.10+, `requests` (runtime), `pytest` + `pytest-mock` + `freezegun` (dev), `setuptools` + `pyproject.toml` (packaging)

---

## File Map

| File | Responsibility |
|---|---|
| `src/newrelic_logger/__init__.py` | Public exports |
| `src/newrelic_logger/exceptions.py` | `NewRelicLoggerError`, `ConfigurationError` |
| `src/newrelic_logger/client.py` | `NewRelicClient` — HTTP, retry, warn |
| `src/newrelic_logger/batch.py` | `BatchQueue` — thread-safe buffer + flush thread |
| `src/newrelic_logger/handler.py` | `NewRelicHandler` — `logging.Handler` subclass |
| `src/newrelic_logger/logger.py` | `NewRelicLogger` — convenience wrapper |
| `tests/test_client.py` | Client unit tests |
| `tests/test_batch.py` | BatchQueue unit tests |
| `tests/test_handler.py` | Handler unit tests |
| `tests/test_logger.py` | Logger unit tests |
| `pyproject.toml` | Package metadata + build config |
| `README.md` | PyPI landing page + usage guide |
| `docs/usage.md` | Extended usage guide |
| `CHANGELOG.md` | Version history |

---

## Task 1: Project scaffold and pyproject.toml

**Files:**
- Create: `pyproject.toml`
- Create: `src/newrelic_logger/__init__.py`
- Create: `tests/__init__.py`
- Create: `CHANGELOG.md`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p src/newrelic_logger tests
touch tests/__init__.py
```

- [ ] **Step 2: Create pyproject.toml**

Create `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "newrelic-logger"
version = "0.1.0"
description = "Send logs to New Relic via their Log REST API"
readme = "README.md"
license = { text = "MIT" }
authors = [{ name = "Your Name", email = "you@example.com" }]
requires-python = ">=3.10"
dependencies = ["requests>=2.28"]
keywords = ["newrelic", "logging", "observability"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: System :: Logging",
]

[project.urls]
Homepage = "https://github.com/yourname/newrelic-logger"
Repository = "https://github.com/yourname/newrelic-logger"

[project.optional-dependencies]
dev = ["pytest>=7.4", "pytest-mock>=3.11", "freezegun>=1.2"]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 3: Create empty `__init__.py`**

Create `src/newrelic_logger/__init__.py`:

```python
# populated in Task 6
```

- [ ] **Step 4: Create CHANGELOG.md**

Create `CHANGELOG.md`:

```markdown
# Changelog

## 0.1.0 (2026-03-26)

- Initial release
- `NewRelicHandler`: drop-in `logging.Handler` for New Relic Log API
- `NewRelicLogger`: standalone convenience logger
- Sync and async (batched) modes
- US and EU region support
- Exponential backoff retry with silent drop
- Global and per-call custom attributes
```

- [ ] **Step 5: Install dev dependencies**

```bash
pip install -e ".[dev]"
```

Expected: installs `requests`, `pytest`, `pytest-mock`, `freezegun` and the package in editable mode.

- [ ] **Step 6: Commit**

```bash
git init
git add pyproject.toml src/newrelic_logger/__init__.py tests/__init__.py CHANGELOG.md
git commit -m "chore: scaffold package structure and pyproject.toml"
```

---

## Task 2: Exceptions

**Files:**
- Create: `src/newrelic_logger/exceptions.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_exceptions.py`:

```python
from newrelic_logger.exceptions import NewRelicLoggerError, ConfigurationError


def test_configuration_error_is_newrelic_logger_error():
    err = ConfigurationError("bad config")
    assert isinstance(err, NewRelicLoggerError)
    assert str(err) == "bad config"


def test_newrelic_logger_error_is_exception():
    err = NewRelicLoggerError("base")
    assert isinstance(err, Exception)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_exceptions.py -v
```

Expected: `ImportError` — module does not exist yet.

- [ ] **Step 3: Implement exceptions**

Create `src/newrelic_logger/exceptions.py`:

```python
class NewRelicLoggerError(Exception):
    """Base exception for newrelic-logger."""


class ConfigurationError(NewRelicLoggerError):
    """Raised when the handler/logger is misconfigured at init time."""
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_exceptions.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add src/newrelic_logger/exceptions.py tests/test_exceptions.py
git commit -m "feat: add exceptions module"
```

---

## Task 3: NewRelicClient — happy path

**Files:**
- Create: `src/newrelic_logger/client.py`
- Create: `tests/test_client.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_client.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from newrelic_logger.client import NewRelicClient


@pytest.fixture
def client():
    return NewRelicClient(api_key="test-key", region="us")


def test_send_posts_to_us_endpoint(client):
    logs = [{"timestamp": 1000, "message": "hello", "level": "INFO", "attributes": {}}]
    with patch("newrelic_logger.client.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=202, ok=True)
        client.send(logs)

    mock_post.assert_called_once()
    url = mock_post.call_args[0][0]
    assert url == "https://log-api.newrelic.com/log/v1"


def test_send_posts_to_eu_endpoint():
    eu_client = NewRelicClient(api_key="test-key", region="eu")
    logs = [{"timestamp": 1000, "message": "hello", "level": "INFO", "attributes": {}}]
    with patch("newrelic_logger.client.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=202, ok=True)
        eu_client.send(logs)

    url = mock_post.call_args[0][0]
    assert url == "https://log-api.eu.newrelic.com/log/v1"


def test_send_sets_api_key_header(client):
    logs = [{"timestamp": 1000, "message": "hello", "level": "INFO", "attributes": {}}]
    with patch("newrelic_logger.client.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=202, ok=True)
        client.send(logs)

    headers = mock_post.call_args[1]["headers"]
    assert headers["Api-Key"] == "test-key"
    assert headers["Content-Type"] == "application/json"


def test_send_builds_correct_payload(client):
    logs = [
        {"timestamp": 1711000000000, "message": "test msg", "level": "ERROR", "attributes": {"x": "1"}},
    ]
    with patch("newrelic_logger.client.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=202, ok=True)
        client.send(logs)

    import json
    payload = json.loads(mock_post.call_args[1]["data"])
    assert payload[0]["logs"][0]["message"] == "test msg"
    assert payload[0]["logs"][0]["level"] == "ERROR"
    assert payload[0]["logs"][0]["timestamp"] == 1711000000000
    assert payload[0]["logs"][0]["attributes"] == {"x": "1"}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_client.py -v
```

Expected: `ImportError` — module does not exist yet.

- [ ] **Step 3: Implement NewRelicClient (happy path only)**

Create `src/newrelic_logger/client.py`:

```python
from __future__ import annotations

import json
import logging
import time

import requests

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
        self._api_key = api_key
        self._endpoint = _ENDPOINTS[region]
        self._timeout = timeout
        self._max_retries = max_retries
        self._backoff_factor = backoff_factor

    def send(self, logs: list[dict]) -> None:
        payload = json.dumps([{"logs": logs}])
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
            except (requests.ConnectionError, requests.Timeout) as exc:
                last_exc = exc

        _internal_logger.warning(
            "newrelic_logger: Failed to send %d log(s) to New Relic after %d retries: %s",
            len(logs),
            self._max_retries,
            str(last_exc),
        )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_client.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/newrelic_logger/client.py tests/test_client.py
git commit -m "feat: add NewRelicClient with happy path"
```

---

## Task 4: NewRelicClient — retry and error handling

**Files:**
- Modify: `tests/test_client.py`

- [ ] **Step 1: Add failing tests for retry behaviour**

Append to `tests/test_client.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_client.py -v
```

Expected: new tests fail — retry count is wrong (current code retries `max_retries + 1` times but test expects `max_retries + 1` total calls including the first attempt). Confirm the logic matches.

- [ ] **Step 3: Verify retry loop is correct**

The current `_post_with_retry` loops `range(self._max_retries + 1)` = 6 iterations (attempt 0..5). This means 1 initial attempt + 5 retries = 6 total calls. Tests assert `call_count == 6`. No code change needed — run tests again to confirm.

```bash
pytest tests/test_client.py -v
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add tests/test_client.py
git commit -m "test: add retry and error handling tests for NewRelicClient"
```

---

## Task 5: BatchQueue

**Files:**
- Create: `src/newrelic_logger/batch.py`
- Create: `tests/test_batch.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_batch.py`:

```python
import time
import threading
from unittest.mock import MagicMock, patch
from newrelic_logger.batch import BatchQueue


def make_client():
    client = MagicMock()
    client.send = MagicMock()
    return client


def test_flush_on_batch_size():
    client = make_client()
    q = BatchQueue(client=client, batch_size=3, flush_interval=60.0)
    try:
        log = {"timestamp": 1000, "message": "x", "level": "INFO", "attributes": {}}
        q.put(log)
        q.put(log)
        q.put(log)  # triggers flush
        time.sleep(0.1)
        client.send.assert_called_once()
        args = client.send.call_args[0][0]
        assert len(args) == 3
    finally:
        q.close()


def test_flush_on_interval():
    client = make_client()
    q = BatchQueue(client=client, batch_size=100, flush_interval=0.1)
    try:
        log = {"timestamp": 1000, "message": "x", "level": "INFO", "attributes": {}}
        q.put(log)
        time.sleep(0.4)  # wait for flush interval
        client.send.assert_called_once()
    finally:
        q.close()


def test_close_flushes_remaining():
    client = make_client()
    q = BatchQueue(client=client, batch_size=100, flush_interval=60.0)
    log = {"timestamp": 1000, "message": "x", "level": "INFO", "attributes": {}}
    q.put(log)
    q.put(log)
    q.close()
    client.send.assert_called_once()
    args = client.send.call_args[0][0]
    assert len(args) == 2


def test_thread_safe_concurrent_puts():
    client = make_client()
    q = BatchQueue(client=client, batch_size=1000, flush_interval=60.0)
    log = {"timestamp": 1000, "message": "x", "level": "INFO", "attributes": {}}
    threads = [threading.Thread(target=q.put, args=(log,)) for _ in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    q.close()
    total_sent = sum(len(call[0][0]) for call in client.send.call_args_list)
    assert total_sent == 50
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_batch.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement BatchQueue**

Create `src/newrelic_logger/batch.py`:

```python
from __future__ import annotations

import queue
import threading
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from newrelic_logger.client import NewRelicClient


class BatchQueue:
    def __init__(
        self,
        client: NewRelicClient,
        batch_size: int = 100,
        flush_interval: float = 5.0,
    ) -> None:
        self._client = client
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._queue: queue.Queue[dict] = queue.Queue()
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def put(self, log: dict) -> None:
        self._queue.put(log)
        if self._queue.qsize() >= self._batch_size:
            self._flush()

    def _run(self) -> None:
        last_flush = time.monotonic()
        while not self._stop_event.is_set():
            elapsed = time.monotonic() - last_flush
            if elapsed >= self._flush_interval:
                self._flush()
                last_flush = time.monotonic()
            time.sleep(0.05)

    def _flush(self) -> None:
        with self._lock:
            batch: list[dict] = []
            try:
                while True:
                    batch.append(self._queue.get_nowait())
            except queue.Empty:
                pass
            if batch:
                self._client.send(batch)

    def flush(self) -> None:
        self._flush()

    def close(self) -> None:
        self._stop_event.set()
        self._thread.join(timeout=5.0)
        self._flush()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_batch.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/newrelic_logger/batch.py tests/test_batch.py
git commit -m "feat: add BatchQueue with background flush thread"
```

---

## Task 6: NewRelicHandler

**Files:**
- Create: `src/newrelic_logger/handler.py`
- Create: `tests/test_handler.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_handler.py`:

```python
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
    sent = handler._client.send.call_args[0][0]
    assert sent[0]["attributes"]["service"] == "svc"


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
    assert sent[0]["attributes"]["env"] == "staging"
    assert sent[0]["attributes"]["req_id"] == "abc"


def test_close_calls_batch_queue_close():
    handler = NewRelicHandler(api_key="key", mode="async")
    handler._batch_queue = MagicMock()
    handler.close()
    handler._batch_queue.close.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_handler.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement NewRelicHandler**

Create `src/newrelic_logger/handler.py`:

```python
from __future__ import annotations

import logging
import time

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
            )

    def emit(self, record: logging.LogRecord) -> None:
        try:
            extra_attrs: dict = getattr(record, "extra_attributes", {}) or {}
            merged_attrs = {**self._global_attributes, **extra_attrs}
            log_dict = {
                "timestamp": int(record.created * 1000),
                "message": self.format(record) if self.formatter else record.getMessage(),
                "level": record.levelname,
                "attributes": merged_attrs,
            }
            if self._mode == "async" and self._batch_queue is not None:
                self._batch_queue.put(log_dict)
            else:
                self._client.send([log_dict])
        except Exception:
            self.handleError(record)

    def close(self) -> None:
        if self._batch_queue is not None:
            self._batch_queue.close()
        super().close()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_handler.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add src/newrelic_logger/handler.py tests/test_handler.py
git commit -m "feat: add NewRelicHandler logging.Handler subclass"
```

---

## Task 7: NewRelicLogger

**Files:**
- Create: `src/newrelic_logger/logger.py`
- Create: `tests/test_logger.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_logger.py`:

```python
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
    sent = logger._handler._client.send.call_args[0][0]
    assert sent[0]["attributes"]["service"] == "svc"
    assert sent[0]["attributes"]["req_id"] == "xyz"


def test_close_flushes_handler():
    logger = make_logger(mode="async")
    logger._handler._batch_queue = MagicMock()
    logger.close()
    logger._handler._batch_queue.close.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_logger.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement NewRelicLogger**

Create `src/newrelic_logger/logger.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_logger.py -v
```

Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add src/newrelic_logger/logger.py tests/test_logger.py
git commit -m "feat: add NewRelicLogger convenience wrapper"
```

---

## Task 8: Wire up public API in `__init__.py`

**Files:**
- Modify: `src/newrelic_logger/__init__.py`

- [ ] **Step 1: Update `__init__.py`**

Replace contents of `src/newrelic_logger/__init__.py`:

```python
from newrelic_logger.handler import NewRelicHandler
from newrelic_logger.logger import NewRelicLogger
from newrelic_logger.exceptions import NewRelicLoggerError, ConfigurationError

__all__ = [
    "NewRelicHandler",
    "NewRelicLogger",
    "NewRelicLoggerError",
    "ConfigurationError",
]

__version__ = "0.1.0"
```

- [ ] **Step 2: Run full test suite**

```bash
pytest -v
```

Expected: all tests pass.

- [ ] **Step 3: Verify imports work from package root**

```bash
python -c "from newrelic_logger import NewRelicLogger, NewRelicHandler, ConfigurationError; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add src/newrelic_logger/__init__.py
git commit -m "feat: wire up public API exports in __init__.py"
```

---

## Task 9: README and usage docs

**Files:**
- Create: `README.md`
- Create: `docs/usage.md`

- [ ] **Step 1: Write README.md**

Create `README.md`:

````markdown
# newrelic-logger

A lightweight Python library for sending logs to [New Relic](https://newrelic.com) via their [Log API](https://docs.newrelic.com/docs/logs/log-api/introduction-log-api/). No New Relic agent required — pure REST API.

## Features

- Works with Python's built-in `logging` module as a drop-in `logging.Handler`
- Standalone `NewRelicLogger` with `.info()`, `.error()` etc.
- US and EU region support
- Sync (immediate) and async (batched, background thread) modes
- Configurable batch size and flush interval
- Exponential backoff retry — never crashes your application
- Global and per-call custom attributes

## Requirements

- Python 3.10+
- `requests`

## Installation

```bash
pip install newrelic-logger
```

## Quick Start

### Standalone logger

```python
from newrelic_logger import NewRelicLogger

logger = NewRelicLogger(
    api_key="YOUR_NEW_RELIC_LICENSE_KEY",
    region="us",               # "us" (default) or "eu"
    mode="async",              # "sync" (default) or "async"
    attributes={"service": "my-app", "environment": "production"},
)

logger.info("Application started")
logger.error("Something went wrong", extra_attributes={"request_id": "abc-123"})

# Always call close() on shutdown to flush buffered logs
logger.close()
```

### As a `logging.Handler`

```python
import logging
from newrelic_logger import NewRelicHandler

handler = NewRelicHandler(
    api_key="YOUR_NEW_RELIC_LICENSE_KEY",
    region="us",
    mode="sync",
    attributes={"service": "my-app"},
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("myapp")
logger.addHandler(handler)

logger.info("Hello from standard logging")
```

## Configuration

| Parameter | Type | Default | Description |
|---|---|---|---|
| `api_key` | `str` | **required** | New Relic license key |
| `region` | `str` | `"us"` | `"us"` or `"eu"` |
| `mode` | `str` | `"sync"` | `"sync"` or `"async"` |
| `batch_size` | `int` | `100` | Max logs per batch (async only) |
| `flush_interval` | `float` | `5.0` | Seconds between flushes (async only) |
| `timeout` | `int` | `10` | HTTP timeout in seconds |
| `max_retries` | `int` | `5` | Max retry attempts on transient failure |
| `backoff_factor` | `float` | `0.5` | Exponential backoff multiplier |
| `attributes` | `dict` | `None` | Global attributes on every log entry |

## Error Handling

The library **never raises exceptions** from logging calls. On failure it retries up to `max_retries` times with exponential backoff, then emits a warning via Python's stdlib `logging` to the `newrelic_logger` logger and silently drops the batch.

To capture these internal warnings:

```python
import logging
logging.getLogger("newrelic_logger").setLevel(logging.WARNING)
```

## License

MIT
````

- [ ] **Step 2: Write docs/usage.md**

Create `docs/usage.md`:

````markdown
# newrelic-logger Usage Guide

## Installation

```bash
pip install newrelic-logger
```

For development:

```bash
git clone https://github.com/yourname/newrelic-logger
cd newrelic-logger
pip install -e ".[dev]"
```

---

## Getting Your New Relic API Key

1. Log in to [New Relic](https://one.newrelic.com)
2. Go to **Profile → API keys**
3. Create or copy a **License key** (type: `INGEST - LICENSE`)
4. Pass it as `api_key` when constructing `NewRelicLogger` or `NewRelicHandler`

---

## Standalone Logger

```python
from newrelic_logger import NewRelicLogger

logger = NewRelicLogger(
    api_key="YOUR_KEY",
    region="us",
    mode="async",
    batch_size=50,
    flush_interval=3.0,
    attributes={"service": "payment-service", "environment": "prod"},
)

# Basic logging
logger.debug("Debug detail")
logger.info("User signed in")
logger.warning("Disk usage above 80%")
logger.error("Failed to process payment")
logger.critical("Database connection lost")

# Per-call extra attributes
logger.info("Request processed", extra_attributes={
    "request_id": "req-xyz",
    "duration_ms": 142,
    "user_id": "u-999",
})

# Always close on shutdown
logger.close()
```

---

## As a `logging.Handler` (drop-in)

```python
import logging
from newrelic_logger import NewRelicHandler

# Create handler
handler = NewRelicHandler(
    api_key="YOUR_KEY",
    region="eu",
    mode="async",
    attributes={"service": "api-gateway"},
)

# Attach to any logger
app_logger = logging.getLogger("myapp")
app_logger.setLevel(logging.DEBUG)
app_logger.addHandler(handler)

# Log normally
app_logger.info("Server started on port 8080")
app_logger.error("Unhandled exception", exc_info=True)

# Shutdown
handler.close()
```

### Passing extra attributes via `logging` extra

```python
app_logger.info(
    "Payment received",
    extra={"extra_attributes": {"amount": 99.99, "currency": "USD"}},
)
```

---

## Sync vs Async Mode

| | Sync | Async |
|---|---|---|
| Blocks caller? | Yes | No |
| Batching | No (1 per call) | Yes |
| Use when | Low-volume, simplicity preferred | High-volume, latency-sensitive |

```python
# Sync — each log call blocks until the HTTP request completes (or retries)
sync_logger = NewRelicLogger(api_key="KEY", mode="sync")

# Async — logs are buffered and flushed in a background thread
async_logger = NewRelicLogger(api_key="KEY", mode="async", batch_size=100, flush_interval=5.0)
```

---

## Regions

```python
# US (default)
logger = NewRelicLogger(api_key="KEY", region="us")
# → https://log-api.newrelic.com/log/v1

# EU
logger = NewRelicLogger(api_key="KEY", region="eu")
# → https://log-api.eu.newrelic.com/log/v1
```

---

## Custom Attributes

Attributes flow in two layers:

1. **Global attributes** — set at init, sent with every log entry
2. **Per-call attributes** — merged at call time, override global on conflict

```python
logger = NewRelicLogger(
    api_key="KEY",
    attributes={"service": "checkout", "env": "prod"},
)

# This log gets: service=checkout, env=staging (override), req_id=abc
logger.info("Order placed", extra_attributes={"env": "staging", "req_id": "abc"})
```

---

## Error Handling

Failed deliveries are **never raised** to the caller. After `max_retries` retries:

```
WARNING:newrelic_logger:newrelic_logger: Failed to send 3 log(s) to New Relic after 5 retries: ...
```

To capture these:

```python
import logging
logging.basicConfig()
logging.getLogger("newrelic_logger").setLevel(logging.WARNING)
```

---

## Graceful Shutdown

Always call `.close()` before your process exits to flush buffered logs:

```python
import atexit
logger = NewRelicLogger(api_key="KEY", mode="async")
atexit.register(logger.close)
```
````

- [ ] **Step 3: Commit**

```bash
git add README.md docs/usage.md
git commit -m "docs: add README and comprehensive usage guide"
```

---

## Task 10: Full test run and PyPI build verification

**Files:** none new

- [ ] **Step 1: Run full test suite**

```bash
pytest -v --tb=short
```

Expected: all tests pass, 0 failures.

- [ ] **Step 2: Verify package builds cleanly**

```bash
pip install build
python -m build
```

Expected: `dist/newrelic_logger-0.1.0.tar.gz` and `dist/newrelic_logger-0.1.0-py3-none-any.whl` created.

- [ ] **Step 3: Verify wheel installs cleanly in a fresh environment**

```bash
pip install dist/newrelic_logger-0.1.0-py3-none-any.whl --force-reinstall
python -c "from newrelic_logger import NewRelicLogger, NewRelicHandler, ConfigurationError; print('Install OK')"
```

Expected: `Install OK`

- [ ] **Step 4: Final commit**

```bash
git add .
git commit -m "chore: verified package builds and installs cleanly for PyPI"
```

---

## Publishing to PyPI (when ready)

```bash
pip install twine
# Test PyPI first
twine upload --repository testpypi dist/*
# Production PyPI
twine upload dist/*
```
