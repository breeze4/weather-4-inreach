"""Poll Gmail IMAP for inReach emails and yield parsed requests."""

import email
import imaplib
import logging
import os
import time
from typing import Generator

from dotenv import load_dotenv

from src.inreach_parser import InReachRequest, parse_body

load_dotenv()

logger = logging.getLogger(__name__)

EXPECTED_SUBJECT = os.environ.get("INREACH_SUBJECT", "inReach message")
POLL_INTERVAL_SECONDS = 120


def _connect() -> imaplib.IMAP4_SSL:
    """Open an authenticated IMAP connection to Gmail."""
    user = os.environ["GMAIL_USER"]
    password = os.environ["GMAIL_APP_PASSWORD"].replace(" ", "")
    conn = imaplib.IMAP4_SSL("imap.gmail.com")
    conn.login(user, password)
    return conn


def fetch_new_requests(conn: imaplib.IMAP4_SSL) -> Generator[InReachRequest, None, None]:
    """Fetch unread emails, filter by subject, parse, mark as read, and yield requests."""
    conn.select("INBOX")
    _status, data = conn.search(None, "UNSEEN")
    if not data or not data[0]:
        return

    for uid in data[0].split():
        _status, msg_data = conn.fetch(uid, "(RFC822)")
        if not msg_data or not msg_data[0]:
            continue

        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)

        subject = msg.get("Subject", "")
        if subject != EXPECTED_SUBJECT:
            # Not an inReach email — ignore but still mark as read
            conn.store(uid, "+FLAGS", "\\Seen")
            continue

        message_id = msg.get("Message-ID", uid.decode())

        # Get plain-text body
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                    break
        else:
            body = msg.get_payload(decode=True).decode("utf-8", errors="replace")

        result = parse_body(body, message_id)

        # Mark as read regardless of whether we got a valid command
        conn.store(uid, "+FLAGS", "\\Seen")

        if result is not None:
            yield result


def poll_loop() -> Generator[InReachRequest, None, None]:
    """Long-running loop: connect, poll every POLL_INTERVAL_SECONDS, yield requests."""
    conn = _connect()
    logger.info("Connected to Gmail IMAP as %s", os.environ["GMAIL_USER"])

    try:
        while True:
            try:
                yield from fetch_new_requests(conn)
            except (imaplib.IMAP4.error, OSError) as exc:
                logger.warning("IMAP error, reconnecting: %s", exc)
                try:
                    conn.logout()
                except Exception:
                    pass
                conn = _connect()

            time.sleep(POLL_INTERVAL_SECONDS)
    finally:
        try:
            conn.logout()
        except Exception:
            pass
