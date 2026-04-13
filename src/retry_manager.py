"""Retry queue for failed NWS forecast requests."""

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

DEFAULT_MAX_ATTEMPTS = 10


@dataclass
class PendingRetry:
    latitude: float
    longitude: float
    command: str
    message_id: str
    reply_url: str
    attempts: int = 0
    max_attempts: int = DEFAULT_MAX_ATTEMPTS


class RetryManager:
    """Manages a queue of requests that need NWS retries."""

    def __init__(self) -> None:
        self._queue: dict[str, PendingRetry] = {}  # keyed by message_id

    def enqueue(self, request) -> None:
        """Add a failed request to the retry queue.

        Args:
            request: an InReachRequest (or any object with latitude, longitude,
                     command, message_id attributes).
        """
        retry = PendingRetry(
            latitude=request.latitude,
            longitude=request.longitude,
            command=request.command,
            message_id=request.message_id,
            reply_url=request.reply_url,
        )
        self._queue[retry.message_id] = retry
        logger.info("Enqueued retry for %s", retry.message_id)

    def get_pending(self) -> list[PendingRetry]:
        """Return all retries that still have attempts remaining."""
        return [r for r in self._queue.values() if r.attempts < r.max_attempts]

    def record_attempt(self, retry: PendingRetry) -> None:
        """Increment the attempt counter for a retry."""
        retry.attempts += 1
        logger.debug(
            "Retry %s attempt %d/%d",
            retry.message_id, retry.attempts, retry.max_attempts,
        )

    def remove(self, retry: PendingRetry) -> None:
        """Remove a retry from the queue (success case)."""
        self._queue.pop(retry.message_id, None)
        logger.info("Removed retry for %s (success)", retry.message_id)

    def cleanup(self) -> None:
        """Remove retries that have exhausted their max attempts."""
        expired = [
            mid for mid, r in self._queue.items()
            if r.attempts >= r.max_attempts
        ]
        for mid in expired:
            logger.warning("Retry exhausted for %s, giving up", mid)
            del self._queue[mid]
