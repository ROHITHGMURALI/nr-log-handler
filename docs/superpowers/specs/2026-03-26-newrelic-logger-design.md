# newrelic-logger Design Spec

**Date:** 2026-03-26
**Status:** Approved

---

## Overview

A PyPI-ready Python package (`newrelic-logger`) for sending logs to New Relic via their Log REST API. No dependency on the `newrelic` agent package. Compatible with Python 3.10+.

---

## Requirements

- Send logs to New Relic Log API using an API key (provided at init, not optional)
- Support US and EU regions, configurable at init
- Integrate with Python's built-in `logging` module as a `logging.Handler`
- Provide a standalone `NewRelicLogger` convenience wrapper with `.info()`, `.error()` etc.
- Support sync (immediate) and async (batched, background thread) modes, configurable at init
- Batch logs with configurable `batch_size` and `flush_interval`
- Retry on transient failures (network errors, 429, 5xx) with exponential backoff
- Default `max_retries=5`, `backoff_factor=0.5`
- After all retries exhausted: log a warning via stdlib `logging`, drop silently (never raise)
- No retry on permanent failures (400, 403)
- Support global custom attributes set at init, overridable per log call
- On `close()`, flush remaining buffered logs before stopping background thread

---

## Package Structure

```
newrelic-logger/
├── src/
│   └── newrelic_logger/
│       ├── __init__.py          # Public API exports
│       ├── handler.py           # NewRelicHandler (logging.Handler subclass)
│       ├── logger.py            # NewRelicLogger (convenience wrapper)
│       ├── client.py            # HTTP client (REST calls to NR Log API)
│       ├── batch.py             # BatchQueue (thread-safe buffer + flush)
│       └── exceptions.py        # NewRelicLoggerError, ConfigurationError
├── tests/
│   ├── test_handler.py
│   ├── test_logger.py
│   ├── test_client.py
│   └── test_batch.py
├── docs/
│   └── usage.md
├── pyproject.toml
├── README.md
└── CHANGELOG.md
```

- `src/` layout prevents accidental imports from project root during testing
- `pyproject.toml` only (no `setup.py`) — modern PyPI standard
- Single runtime dependency: `requests`
- Python `>=3.10` constraint

---

## Components

### `client.py` — `NewRelicClient`

Owns all HTTP interaction.

**Init params:**
- `api_key: str`
- `region: str` — `"us"` | `"eu"`
- `timeout: int` — seconds (default: 10)
- `max_retries: int` — default: 5
- `backoff_factor: float` — default: 0.5

**Method:** `send(logs: list[dict]) -> None`

- Builds New Relic Log API JSON payload
- POSTs to correct regional endpoint with `Api-Key` header
- Retries on: `ConnectionError`, `Timeout`, HTTP 429, HTTP 5xx
- No retry on: HTTP 400, HTTP 403
- After exhausting retries: emits stdlib `logging.warning(...)`, drops silently

**Endpoints:**
- US: `https://log-api.newrelic.com/log/v1`
- EU: `https://log-api.eu.newrelic.com/log/v1`

---

### `batch.py` — `BatchQueue`

Thread-safe log buffer with background flush thread.

**Init params:**
- `client: NewRelicClient`
- `batch_size: int` — flush when this many records accumulate (default: 100)
- `flush_interval: float` — flush every N seconds regardless of size (default: 5.0)

**Behavior:**
- Uses `queue.Queue` for thread safety
- Background daemon thread flushes on `batch_size` OR `flush_interval` elapsed
- `flush()` — drain all pending records immediately
- `close()` — flush remaining records, stop background thread cleanly

**Bypassed in sync mode** — records go directly to `NewRelicClient`.

---

### `handler.py` — `NewRelicHandler`

Subclasses `logging.Handler`. Primary integration point for standard `logging` setups.

**Init params:**
- `api_key: str` — **required**, raises `ConfigurationError` if missing
- `region: str` — `"us"` | `"eu"` (default: `"us"`)
- `mode: str` — `"sync"` | `"async"` (default: `"sync"`)
- `batch_size: int` — default: 100 (async only)
- `flush_interval: float` — default: 5.0 seconds (async only)
- `timeout: int` — HTTP timeout in seconds (default: 10)
- `max_retries: int` — default: 5
- `backoff_factor: float` — default: 0.5
- `attributes: dict` — global custom attributes merged into every log entry

**`emit(record: logging.LogRecord) -> None`:**
- Formats record into NR log dict
- Merges `global_attributes` + per-call `extra_attributes` (from `record.extra_attributes` if present)
- Routes to `NewRelicClient.send()` (sync) or `BatchQueue.put()` (async)

**`close() -> None`:**
- Flushes remaining batch items (async mode)
- Stops background thread
- Calls `super().close()`

---

### `logger.py` — `NewRelicLogger`

Convenience wrapper. Creates an internal `logging.Logger` and attaches a `NewRelicHandler`.

**Init params:** Same as `NewRelicHandler`.

**Methods:**
- `debug(msg, extra_attributes=None)`
- `info(msg, extra_attributes=None)`
- `warning(msg, extra_attributes=None)`
- `error(msg, extra_attributes=None)`
- `critical(msg, extra_attributes=None)`
- `close()`

`extra_attributes` dict is merged with global attributes at the per-log level.

---

### `exceptions.py`

- `NewRelicLoggerError` — base exception
- `ConfigurationError(NewRelicLoggerError)` — raised at init for invalid config (missing `api_key`, invalid `region`, invalid `mode`)

---

## API Payload Format

```json
[{
  "common": {
    "attributes": {
      "service": "my-app",
      "environment": "prod"
    }
  },
  "logs": [
    {
      "timestamp": 1711234567890,
      "message": "Something happened",
      "level": "INFO",
      "attributes": {
        "request_id": "abc-123"
      }
    }
  ]
}]
```

- `common.attributes` = global attributes set at init
- Per-log `attributes` = `extra_attributes` passed per call
- `timestamp` = milliseconds since epoch (UTC)
- `level` = stdlib log level name (e.g., `"INFO"`, `"ERROR"`)

---

## Error Handling & Retry

| Failure Type | Retry? | After Exhaustion |
|---|---|---|
| `ConnectionError`, `Timeout` | Yes | Warn + drop |
| HTTP 429 (rate limit) | Yes | Warn + drop |
| HTTP 5xx (server error) | Yes | Warn + drop |
| HTTP 400 (bad payload) | No | Warn + drop |
| HTTP 403 (invalid API key) | No | Warn + drop |

**Backoff formula:** `wait = backoff_factor * (2 ** attempt)`
With defaults (`backoff_factor=0.5`): 0.5s → 1s → 2s → 4s → 8s

**Warning message (after all retries):**
```
newrelic_logger: Failed to send N log(s) to New Relic after 5 retries: <error>
```

**Init-time validation (fail fast):**
- Missing `api_key` → `ConfigurationError`
- Invalid `region` → `ConfigurationError`
- Invalid `mode` → `ConfigurationError`

---

## Testing Strategy

**Framework:** `pytest`
**Dev dependencies:** `pytest`, `pytest-mock`, `freezegun`

| Test file | Coverage |
|---|---|
| `test_client.py` | Payload shape, headers, retry on 429/5xx, no retry on 400/403, stdlib warning after exhaustion |
| `test_batch.py` | Flush on `batch_size`, flush on `flush_interval`, thread-safe concurrent puts |
| `test_handler.py` | Sync vs async routing, attribute merging, `close()` flushes remaining items |
| `test_logger.py` | Convenience methods pass correct level and `extra_attributes` |

No live API calls in tests — all HTTP mocked.

---

## Public API Summary

```python
from newrelic_logger import NewRelicLogger, NewRelicHandler, ConfigurationError

# Standalone logger
logger = NewRelicLogger(
    api_key="YOUR_KEY",
    region="us",          # "us" | "eu"
    mode="async",         # "sync" | "async"
    batch_size=100,
    flush_interval=5.0,
    attributes={"service": "my-app", "env": "prod"},
)
logger.info("Hello", extra_attributes={"request_id": "abc"})
logger.close()

# As a logging.Handler
import logging
handler = NewRelicHandler(api_key="YOUR_KEY", region="eu", mode="sync")
logging.getLogger("myapp").addHandler(handler)
```
