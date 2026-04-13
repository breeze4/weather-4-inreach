# Reply Sender + Main Loop + Retry

## Parent spec

`docs/specs/2026-04-12-01-weather-bot-v1.md`

## What to build

The orchestration layer that wires everything together: the main poll loop, SMTP reply sender, and NWS retry manager. The main loop runs forever, polling Gmail every 2 minutes, processing requests through the parse→fetch→format→send pipeline, and managing a retry queue for NWS failures.

## Type

AFK

## Blocked by

- Blocked by `2026-04-12-01-email-ingestion-parse.md`
- Blocked by `2026-04-12-02-nws-forecast-fetch.md`
- Blocked by `2026-04-12-03-gemini-formatter.md`

## User stories addressed

- User story 4 (response within a few minutes)
- User story 5 (error messages when something breaks)
- User story 6 (automatic NWS retry for 20 minutes)
- User story 8 (runs unattended)

## Acceptance criteria

- [x] Sends formatted forecast as a new email via SMTP to the configured `INREACH_EMAIL`
- [x] SMTP uses the same Gmail credentials from `.env`
- [x] Reply email body is just the forecast text, no extra formatting or signatures
- [x] Main loop polls every 2 minutes, processes all unread matching emails each cycle
- [x] On NWS failure: immediately sends error message to InReach ("NWS unavailable, retrying 20min")
- [x] On NWS failure: enqueues retry, attempts every 2 minutes for up to 10 tries
- [x] On retry success: sends the formatted forecast
- [x] On retry exhaustion (10 failures): gives up silently (initial error already sent)
- [x] On Gemini failure (all 3 format attempts fail): sends error message to InReach
- [x] Process handles IMAP connection drops gracefully (reconnect on next cycle)
- [x] Process logs actions to stdout for systemd journal capture
- [x] InReach reply address read from `.env`

## Owns

- `src/reply_sender.py` — SMTP connection, send email to InReach address
- `src/retry_manager.py` — retry queue, attempt tracking, expiry logic
- `src/main.py` — main loop, orchestration, logging
- `tests/test_retry_manager.py` — retry state machine unit tests
- `.env.example` — add `INREACH_EMAIL` placeholder

## Must not touch

- `src/email_poller.py` — owned by plan `2026-04-12-01-email-ingestion-parse.md`
- `src/inreach_parser.py` — owned by plan `2026-04-12-01-email-ingestion-parse.md`
- `src/nws_client.py` — owned by plan `2026-04-12-02-nws-forecast-fetch.md`
- `src/formatter.py` — owned by plan `2026-04-12-03-gemini-formatter.md`

## Defines interfaces

None — this plan consumes all other modules' interfaces.

## Pattern exemplar

None — first of its kind. The deploy-to-beebaby skill describes the systemd service pattern for the process lifecycle.

## Tasks

- [x] Add `INREACH_EMAIL` to `.env.example`
- [x] Implement `reply_sender.py`: SMTP connect using Gmail creds, send plain-text email to InReach address
- [x] Implement `retry_manager.py`: dataclass for pending retries (lat, lon, command, attempts, max_attempts=10), enqueue/dequeue/expire methods
- [x] Write unit tests for retry manager: enqueue, increment attempts, expiry at 10, concurrent retries for different requests
- [x] Implement `main.py`: load `.env`, main loop with 2-minute sleep, poll→parse→fetch→format→send pipeline
- [x] Add NWS error handling in main loop: catch NWS exceptions, send error message, enqueue retry
- [x] Add Gemini error handling: catch formatter exceptions, send error message
- [x] Add retry processing to each loop cycle: check pending retries, attempt NWS fetch, send on success
- [x] Add logging (print to stdout) for key events: poll, parse, fetch, format, send, retry, error
- [x] Add IMAP reconnect logic: catch connection errors, reconnect on next cycle
- [ ] Manual end-to-end test: send real InReach email, verify forecast reply arrives
