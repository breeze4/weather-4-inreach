"""Parse inReach email bodies to extract weather commands and GPS coordinates."""

import re
from dataclasses import dataclass
from typing import Optional

VALID_COMMANDS = {"wx now", "wx week"}
LATLON_RE = re.compile(r"Lat\s+([-\d.]+)\s+Lon\s+([-\d.]+)")
REPLY_URL_RE = re.compile(r"https://inreachlink\.com/\S+")


@dataclass
class InReachRequest:
    command: str        # "wx now" or "wx week"
    latitude: float
    longitude: float
    message_id: str
    reply_url: str      # inreachlink.com URL for replying to this message


def parse_body(body: str, message_id: str) -> Optional[InReachRequest]:
    """Extract command and lat/lon from an inReach email body.

    Returns an InReachRequest if the body contains a recognized command
    and a valid lat/lon line.  Returns None otherwise.
    """
    # Command is the first non-empty line
    command = None
    for line in body.splitlines():
        stripped = line.strip()
        if stripped:
            command = stripped.lower()
            break

    if command not in VALID_COMMANDS:
        return None

    match = LATLON_RE.search(body)
    if match is None:
        return None

    url_match = REPLY_URL_RE.search(body)
    if url_match is None:
        return None

    return InReachRequest(
        command=command,
        latitude=float(match.group(1)),
        longitude=float(match.group(2)),
        message_id=message_id,
        reply_url=url_match.group(0),
    )
