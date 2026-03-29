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
        common_attributes: dict | None = None,
    ) -> None:
        self._client = client
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._common_attributes = common_attributes
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
                self._client.send(batch, common_attributes=self._common_attributes)

    def flush(self) -> None:
        self._flush()

    def close(self) -> None:
        self._stop_event.set()
        self._thread.join(timeout=5.0)
        self._flush()
