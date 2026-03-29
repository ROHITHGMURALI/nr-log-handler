# nr-log-handler Usage Guide

## Installation

```bash
pip install nr-log-handler
```

For development:

```bash
git clone https://github.com/yourname/nr-log-handler
cd nr-log-handler
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
