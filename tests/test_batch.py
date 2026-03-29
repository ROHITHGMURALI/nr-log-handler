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
        time.sleep(1.0)  # increased from 0.4 to 1.0 for CI reliability
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
