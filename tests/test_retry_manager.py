"""Tests for the retry manager state machine."""

from dataclasses import dataclass

from src.retry_manager import RetryManager, PendingRetry


@dataclass
class FakeRequest:
    latitude: float = 47.0
    longitude: float = -122.0
    command: str = "wx now"
    message_id: str = "msg-1"
    reply_url: str = "https://inreachlink.com/test"


class TestRetryManager:
    def test_enqueue_appears_in_pending(self):
        rm = RetryManager()
        rm.enqueue(FakeRequest())
        pending = rm.get_pending()
        assert len(pending) == 1
        assert pending[0].message_id == "msg-1"
        assert pending[0].attempts == 0

    def test_record_attempt_increments_count(self):
        rm = RetryManager()
        rm.enqueue(FakeRequest())
        retry = rm.get_pending()[0]
        rm.record_attempt(retry)
        assert retry.attempts == 1
        rm.record_attempt(retry)
        assert retry.attempts == 2

    def test_remove_takes_out_of_queue(self):
        rm = RetryManager()
        rm.enqueue(FakeRequest())
        retry = rm.get_pending()[0]
        rm.remove(retry)
        assert rm.get_pending() == []

    def test_cleanup_removes_exhausted_retries(self):
        rm = RetryManager()
        rm.enqueue(FakeRequest())
        retry = rm.get_pending()[0]
        for _ in range(retry.max_attempts):
            rm.record_attempt(retry)
        # At max attempts, get_pending should exclude it
        assert rm.get_pending() == []
        # cleanup removes it from the queue entirely
        rm.cleanup()
        # Verify internal queue is empty
        assert rm._queue == {}

    def test_multiple_concurrent_retries(self):
        rm = RetryManager()
        rm.enqueue(FakeRequest(message_id="msg-a", latitude=47.0))
        rm.enqueue(FakeRequest(message_id="msg-b", latitude=48.0))
        rm.enqueue(FakeRequest(message_id="msg-c", latitude=49.0))

        pending = rm.get_pending()
        assert len(pending) == 3

        # Succeed one, fail another, leave third alone
        for r in pending:
            if r.message_id == "msg-a":
                rm.remove(r)
            elif r.message_id == "msg-b":
                rm.record_attempt(r)

        pending = rm.get_pending()
        ids = {r.message_id for r in pending}
        assert "msg-a" not in ids  # removed
        assert "msg-b" in ids     # still retrying
        assert "msg-c" in ids     # untouched

    def test_get_pending_excludes_maxed_out(self):
        rm = RetryManager()
        req = FakeRequest(message_id="msg-x")
        rm.enqueue(req)
        retry = rm.get_pending()[0]
        retry.max_attempts = 2
        rm.record_attempt(retry)
        rm.record_attempt(retry)
        assert rm.get_pending() == []

    def test_enqueue_overwrites_same_message_id(self):
        rm = RetryManager()
        rm.enqueue(FakeRequest(message_id="msg-1", latitude=10.0))
        rm.enqueue(FakeRequest(message_id="msg-1", latitude=20.0))
        pending = rm.get_pending()
        assert len(pending) == 1
        assert pending[0].latitude == 20.0
