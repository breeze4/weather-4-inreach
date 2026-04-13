# Gemini Formatter + Validation

## Parent spec

`docs/specs/2026-04-12-01-weather-bot-v1.md`

## What to build

A module that takes NWS forecast periods and the command type, sends them to Gemini 3.1 Flash with a formatting prompt, validates the output fits the 160-character InReach message limit and matches the expected format, and retries up to 3 times if validation fails.

## Type

AFK

## Blocked by

None — can start immediately (develop with mock forecast data)

## User stories addressed

- User story 1 (24-hour forecast)
- User story 2 (multi-day forecast)
- User story 3 (precip percentage in output)

## Acceptance criteria

- [ ] Accepts command type (`wx now` or `wx week`) and a list of forecast periods
- [ ] Constructs a Gemini prompt with the forecast data, format examples, and the 160-char constraint
- [ ] Calls Gemini 3.1 Flash API and gets the formatted response
- [ ] Validates response is ≤160 characters
- [ ] Validates response contains recognizable day abbreviations and temperatures
- [ ] Retries with correction instructions up to 3 total attempts if validation fails
- [ ] Raises an exception if all 3 attempts fail validation
- [ ] `wx now` output includes precip % when precipitation is forecasted
- [ ] `wx week` output packs as many day/night periods as fit, truncating from the end
- [ ] Unit tests pass for the validation logic
- [ ] Gemini API key read from `.env`

## Owns

- `src/formatter.py` — Gemini API call, prompt template, validation, retry loop
- `tests/test_formatter.py` — validation logic unit tests

## Must not touch

- `src/email_poller.py` — owned by plan `2026-04-12-01-email-ingestion-parse.md`
- `src/inreach_parser.py` — owned by plan `2026-04-12-01-email-ingestion-parse.md`
- `src/nws_client.py` — owned by plan `2026-04-12-02-nws-forecast-fetch.md`
- `src/main.py` — owned by plan `2026-04-12-04-main-loop-reply-retry.md`

## Defines interfaces

- **format_forecast function** in `src/formatter.py` — consumed by plan `2026-04-12-04`

## Pattern exemplar

None — first of its kind. The old service's message format (from the spec screenshots) is the style reference:

```
Td RnShw 58% 57 Tn RnShw 39% 41 Wed ChRn 40% 55 WedN MCldy 18% 43
```

## Tasks

- [x] ~~Add `GEMINI_API_KEY` to `.env.example`~~ Skipped per instructions — documented in handoff
- [x] Build the Gemini prompt template for `wx now` — include format examples, 160-char limit, precip % requirement
- [x] Build the Gemini prompt template for `wx week` — include format examples, 160-char limit, pack-as-many-as-fit instruction
- [x] Implement validation function: check ≤160 chars, check for day abbreviations and temperature numbers
- [x] Implement `format_forecast(command, periods)`: call Gemini, validate, retry with correction if invalid
- [x] Write unit tests for the validation function with known good/bad outputs
- [ ] Manual test with real NWS data to verify Gemini output quality

## Implementation notes

The prompt should be explicit about the format. Include 2-3 examples of good output for each command type. Tell Gemini:
- Exactly 160 char max (not "around 160")
- Use abbreviated day names (Mon, Tue, etc.) and short condition codes
- Include precip % only when > 0%
- For `wx week`, start from today and pack as many periods as fit — do not exceed 160 chars, just stop adding periods

The validation function should be simple:
1. `len(message) <= 160`
2. Contains at least one temperature number (regex `\d{2,3}`)
3. Contains at least one day-like abbreviation

On retry, send the previous output back with: "This was {len} chars, max is 160. Shorten it while keeping the same format."
