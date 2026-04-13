"""Send replies to InReach devices via the Garmin reply page."""

import logging
import os
from html.parser import HTMLParser

import requests

logger = logging.getLogger(__name__)

TIMEOUT = 15


class _GuidFinder(HTMLParser):
    """Extract the Guid hidden field from the Garmin reply page."""

    def __init__(self):
        super().__init__()
        self.guid = None

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "input" and d.get("name") == "Guid":
            self.guid = d.get("value")


def send_reply(body: str, reply_url: str) -> None:
    """Send a message to an InReach device via the Garmin reply page.

    Args:
        body: The message text to send.
        reply_url: The inreachlink.com URL from the original email.
    """
    from_addr = os.environ["GMAIL_USER"]

    # Step 1: GET the reply page, extract Guid
    resp = requests.get(reply_url, timeout=TIMEOUT)
    resp.raise_for_status()

    parser = _GuidFinder()
    parser.feed(resp.text)
    if not parser.guid:
        raise RuntimeError(f"Could not find Guid on reply page: {reply_url}")

    # Step 2: POST the reply
    payload = {
        "Guid": parser.guid,
        "ReplyAddress": from_addr,
        "ReplyMessage": body,
    }
    post_url = resp.url.split("?")[0]  # same page, no query params
    post_resp = requests.post(post_url, data=payload, timeout=TIMEOUT)
    post_resp.raise_for_status()

    logger.info("Sent reply via %s (%d chars)", reply_url, len(body))
