# Step 4 Handoff: Main Loop + Reply Sender + Retry Manager

## Files created

- `src/reply_sender.py` — sends plain-text email to InReach via Gmail SMTP_SSL on port 465
- `src/retry_manager.py` — in-memory retry queue keyed by message_id, 10 attempts max
- `src/main.py` — main loop orchestrating poll→fetch→format→send with retry handling
- `tests/test_retry_manager.py` — 7 unit tests covering enqueue, attempt tracking, removal, cleanup, concurrent retries

## Files modified

- `.env.example` — added `GEMINI_API_KEY` and `INREACH_EMAIL`

## Complete `.env.example` contents

```
GMAIL_USER=your_email@gmail.com
GMAIL_APP_PASSWORD=your_app_password_here
GEMINI_API_KEY=your_gemini_api_key
INREACH_EMAIL=yourdevice@inreach.garmin.com
```

## Key decisions

- `main.py` manages its own IMAP connection rather than using `poll_loop()`, so it can interleave retry processing between poll cycles.
- Retry queue is in-memory (dict keyed by message_id). Restarts lose pending retries, which is acceptable since the 20-minute retry window is short.
- On NWS failure: sends "NWS unavailable, retrying 20min" immediately, then enqueues for retry.
- On formatter failure: sends "Format error" to InReach, no retry (Gemini failures are unlikely to self-resolve).
- On retry exhaust (10 attempts): silently drops the retry since the user already got the error notification.
- IMAP reconnection: on any IMAP/OS error, logs out and sets conn to None; next loop iteration reconnects.
- Logging goes to stdout via `logging.basicConfig` for systemd journal capture.

## Integration notes

- Imports `_connect` from `email_poller` (underscore-prefixed but needed for connection management).
- `load_dotenv()` is called at module level in `main.py` before other src imports, ensuring env vars are available.

## Test results

All 23 tests pass: 8 parser, 8 formatter, 7 retry manager.
