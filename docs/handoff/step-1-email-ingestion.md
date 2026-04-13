# Step 1 Handoff: Email Ingestion + Parse

## Files created

- `src/inreach_parser.py` — command/lat-lon extraction from email body
- `src/email_poller.py` — IMAP connection, poll, filter by subject, mark-as-read
- `tests/test_inreach_parser.py` — 8 unit tests for the parser
- `src/__init__.py` — package marker (empty)
- `tests/__init__.py` — package marker (empty)
- `.env.example` — template with `GMAIL_USER` and `GMAIL_APP_PASSWORD`

## Parsed request dataclass

```
InReachRequest (from src.inreach_parser)
    command: str        # "wx now" or "wx week" (always lowercase)
    latitude: float     # e.g. 47.756259
    longitude: float    # e.g. -122.350252
    message_id: str     # email Message-ID header value
```

Import: `from src.inreach_parser import InReachRequest, parse_body`

## Key functions

- `parse_body(body: str, message_id: str) -> Optional[InReachRequest]` — returns None for unrecognized commands or missing coordinates
- `fetch_new_requests(conn: imaplib.IMAP4_SSL) -> Generator[InReachRequest, None, None]` — single poll pass
- `poll_loop() -> Generator[InReachRequest, None, None]` — long-running loop, yields requests every 2 minutes

## Decisions made

- Command is always stored lowercase regardless of input casing
- Non-inReach emails are marked as read but not processed (prevents re-fetching)
- Emails with recognized subject but unrecognized command are marked as read and silently skipped
- `poll_loop` reconnects automatically on IMAP errors
- `python-dotenv` loads `.env` at module import time in `email_poller.py`
