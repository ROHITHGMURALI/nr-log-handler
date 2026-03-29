# nr-log-handler

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
pip install nr-log-handler
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

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for release history.

### Latest: 0.1.1 (2026-03-29)

- Fixed deprecated `license` table format in `pyproject.toml` (SPDX string)
- Added `LICENSE` file (MIT)
- Added GitHub Actions workflow for automated PyPI publishing

## License

MIT
