# Email Ingestion + Parse

## Parent spec

`docs/specs/2026-04-12-01-weather-bot-v1.md`

## What to build

A module that connects to Gmail via IMAP, polls for unread emails every 2 minutes, filters by subject line, extracts the command (`wx now` or `wx week`) and GPS coordinates from the email body, and marks processed emails as read. This is the ingestion boundary — everything downstream receives a clean parsed request.

## Type

AFK

## Blocked by

None — can start immediately

## User stories addressed

- User story 4 (response within a few minutes)
- User story 7 (malformed/non-InReach emails silently ignored)

## Acceptance criteria

- [ ] Connects to Gmail IMAP using App Password credentials from `.env`
- [ ] Fetches only unread emails
- [ ] Filters emails by subject `inReach message from Jane Doe` — all others ignored
- [ ] Extracts command (`wx now` or `wx week`) case-insensitively from email body
- [ ] Emails with unrecognized commands are silently ignored (no reply, marked as read)
- [ ] Extracts lat/lon from the line `Jane Doe sent this message from: Lat XX.XXXXXX Lon -XXX.XXXXXX`
- [ ] Marks email as read after yielding the parsed request
- [ ] Returns a structured object: command enum, latitude, longitude, message ID
- [ ] Unit tests pass for the parser using the sample `.eml` fixture

## Owns

- `src/email_poller.py` — IMAP connection, poll, filter, mark-as-read
- `src/inreach_parser.py` — command extraction, lat/lon extraction
- `tests/test_inreach_parser.py` — parser unit tests
- `.env.example` — template with `GMAIL_USER`, `GMAIL_APP_PASSWORD` placeholders

## Must not touch

- `src/nws_client.py` — owned by plan `2026-04-12-02-nws-forecast-fetch.md`
- `src/formatter.py` — owned by plan `2026-04-12-03-gemini-formatter.md`
- `src/reply_sender.py` — owned by plan `2026-04-12-04-main-loop-reply-retry.md`
- `src/main.py` — owned by plan `2026-04-12-04-main-loop-reply-retry.md`

## Defines interfaces

- **Parsed request dataclass** (command enum + lat + lon + message_id) in `src/inreach_parser.py` — consumed by plans `2026-04-12-04`

## Pattern exemplar

None — first of its kind, refer to spec for interface requirements. The sample email at `docs/inReach message from Jane Doe.eml` is the definitive reference for parsing logic.

## Tasks

- [ ] Create `.env.example` with `GMAIL_USER` and `GMAIL_APP_PASSWORD` placeholders
- [ ] Implement `inreach_parser.py`: function to parse email body, extract command (case-insensitive) and lat/lon, return dataclass or None
- [ ] Write unit tests for parser against the sample `.eml` file — test recognized commands, unrecognized commands, case variations, lat/lon extraction
- [ ] Implement `email_poller.py`: IMAP connect, fetch unread, filter by subject, yield parsed requests, mark as read
- [ ] Manual test: send a test email to the Gmail account and verify the poller picks it up and parses correctly

## Implementation notes

The email body format (from the sample `.eml`):
```
Wx now

View the location or send a reply to Jane Doe:
https://inreachlink.com/gifNuqslgVb6olfzfJevecA

Jane Doe sent this message from: Lat 47.756259 Lon -122.350252
```

The command is the first non-empty line of the body. The lat/lon line has a consistent format — a simple regex like `Lat\s+([-\d.]+)\s+Lon\s+([-\d.]+)` should work.
