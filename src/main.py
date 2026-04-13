"""Main loop: poll Gmail, fetch weather, format via Gemini, reply via SMTP."""

import imaplib
import logging
import threading
import time

from dotenv import load_dotenv

load_dotenv()

import uvicorn

from src.api import app as api_app
from src.email_poller import fetch_new_requests, _connect, POLL_INTERVAL_SECONDS
from src.formatter import format_forecast, FormatterError
from src.nws_client import fetch_forecast, NWSError
from src.reply_sender import send_reply
from src.retry_manager import RetryManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _process_request(request, retry_manager: RetryManager) -> None:
    """Run the fetch→format→send pipeline for a single request."""
    logger.info(
        "Processing %s for (%.4f, %.4f) [%s]",
        request.command, request.latitude, request.longitude, request.message_id,
    )

    try:
        periods = fetch_forecast(request.latitude, request.longitude)
    except NWSError as exc:
        logger.error("NWS error for %s: %s", request.message_id, exc)
        try:
            send_reply("NWS unavailable, retrying 20min", request.reply_url)
        except Exception as send_exc:
            logger.error("Failed to send NWS error notification: %s", send_exc)
        retry_manager.enqueue(request)
        return

    try:
        message = format_forecast(request.command, periods)
    except FormatterError as exc:
        logger.error("Formatter error for %s: %s", request.message_id, exc)
        try:
            send_reply("Format error", request.reply_url)
        except Exception as send_exc:
            logger.error("Failed to send format error notification: %s", send_exc)
        return

    try:
        send_reply(message, request.reply_url)
    except Exception as exc:
        logger.error("Reply error for %s: %s", request.message_id, exc)


def _process_retries(retry_manager: RetryManager) -> None:
    """Attempt pending retries: fetch→format→send."""
    pending = retry_manager.get_pending()
    if not pending:
        return

    logger.info("Processing %d pending retries", len(pending))

    for retry in pending:
        retry_manager.record_attempt(retry)
        try:
            periods = fetch_forecast(retry.latitude, retry.longitude)
        except NWSError as exc:
            logger.warning(
                "Retry %s attempt %d/%d failed: %s",
                retry.message_id, retry.attempts, retry.max_attempts, exc,
            )
            continue

        try:
            message = format_forecast(retry.command, periods)
        except FormatterError as exc:
            logger.error("Formatter error on retry %s: %s", retry.message_id, exc)
            retry_manager.remove(retry)
            try:
                send_reply("Format error", retry.reply_url)
            except Exception:
                pass
            continue

        try:
            send_reply(message, retry.reply_url)
            retry_manager.remove(retry)
        except Exception as exc:
            logger.error("Reply error on retry %s: %s", retry.message_id, exc)

    retry_manager.cleanup()


def main() -> None:
    """Run the main poll loop."""
    retry_manager = RetryManager()
    conn = None

    logger.info("Weather bot starting")

    while True:
        # Ensure IMAP connection
        if conn is None:
            try:
                conn = _connect()
                logger.info("Connected to Gmail IMAP")
            except Exception as exc:
                logger.error("IMAP connect failed: %s", exc)
                time.sleep(POLL_INTERVAL_SECONDS)
                continue

        # Poll for new requests
        try:
            for request in fetch_new_requests(conn):
                _process_request(request, retry_manager)
        except (imaplib.IMAP4.error, OSError) as exc:
            logger.warning("IMAP error during poll, will reconnect: %s", exc)
            try:
                conn.logout()
            except Exception:
                pass
            conn = None

        # Process retries
        _process_retries(retry_manager)

        logger.info("Sleeping %ds", POLL_INTERVAL_SECONDS)
        time.sleep(POLL_INTERVAL_SECONDS)


def _run_api():
    """Run the FastAPI server in a background thread."""
    uvicorn.run(api_app, host="0.0.0.0", port=8035, log_level="info")


if __name__ == "__main__":
    api_thread = threading.Thread(target=_run_api, daemon=True)
    api_thread.start()
    main()
