# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run a single test file
pytest tests/test_handler.py

# Run a single test by name
pytest tests/test_handler.py::TestNewRelicHandler::test_emit_sync

# Build distribution packages
python -m build
```

## Architecture

This is a Python package (`nr-log-handler`) that ships log records to New Relic's Log REST API. Package source lives under `src/newrelic_logger/` and is installed as `newrelic_logger`.

**Data flow (sync mode):**
`NewRelicLogger` → `NewRelicHandler.emit()` → `NewRelicClient.send()` → New Relic HTTP API

**Data flow (async mode):**
`NewRelicLogger` → `NewRelicHandler.emit()` → `BatchQueue.put()` → background thread → `NewRelicClient.send()` → New Relic HTTP API

### Key modules

- **`handler.py`** — `NewRelicHandler(logging.Handler)`: the standard Python logging handler. Validates config, owns a `NewRelicClient`, and optionally a `BatchQueue` (async mode). `emit()` builds the log dict and either sends immediately (sync) or enqueues (async).
- **`client.py`** — `NewRelicClient`: sends a list of log dicts to the New Relic Log API (`/log/v1`). Implements exponential-backoff retry; treats HTTP 400/403 as permanent failures (no retry). Supports `us`/`eu` regions.
- **`batch.py`** — `BatchQueue`: thread-safe queue with a daemon background thread. Flushes when `batch_size` is reached or `flush_interval` seconds elapse. `close()` stops the thread then does a final flush.
- **`logger.py`** — `NewRelicLogger`: convenience wrapper that creates a dedicated `logging.Logger` (with a UUID name to prevent collisions) and attaches `NewRelicHandler` to it. Exposes `debug/info/warning/error/critical(msg, extra_attributes)`.
- **`exceptions.py`** — `NewRelicLoggerError` (base), `ConfigurationError`.

### Log payload shape

Each log entry sent to New Relic:
```json
[{"logs": [{"timestamp": <ms>, "message": "...", "level": "INFO", "attributes": {...}}],
  "common": {"attributes": {...}}}]
```

`attributes` comes from per-call `extra_attributes`; `common.attributes` comes from handler-level `attributes` dict.

### Internal logging

The library logs its own warnings (send failures, retries) to the `newrelic_logger` stdlib logger, so they never recurse into the handler itself.
