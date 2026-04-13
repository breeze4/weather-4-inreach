# Deterministic NWS Formatter

## Parent spec

`docs/specs/2026-04-12-02-deterministic-formatter.md`

## What to build

A deterministic formatter that abbreviates NWS forecast periods into ≤160-char satellite messages without any LLM call. Lookup tables map day names and shortForecast conditions to short codes. Probability prefixes are stripped (precip_chance is already a separate field). Compound "then" forecasts take only the first part. Unknown conditions get a 3-char fallback. An env var switch (`USE_GEMINI_FORMATTER=true`) preserves the Gemini path as an option.

## Type

AFK

## Blocked by

None - can start immediately

## User stories addressed

N/A — lightweight spec, no user stories. Covers all sections of parent spec.

## Acceptance criteria

- [x] `DAY_MAP` correctly abbreviates all NWS period names (Today, Tonight, This Afternoon, weekday, weekday Night)
- [x] `CONDITION_MAP` covers all conditions listed in spec (sky, rain, snow/ice, freezing, thunderstorms, visibility, wind/temp)
- [x] Probability prefixes (Slight Chance, Chance, Likely, Isolated, Scattered, Numerous, Areas, Patchy) stripped before condition lookup
- [x] Compound "then" forecasts split, only first part used
- [x] Unknown conditions produce 3-char abbreviation (first letter of each word; single words use first 3 letters)
- [x] Token format per period: `DayCode CondCode Precip% Temp` (precip% only when > 0)
- [x] `wx now` formats first 4 periods
- [x] `wx week` formats all periods, truncated at token boundary to 160 chars
- [x] `format_forecast` dispatches to deterministic path by default
- [x] `USE_GEMINI_FORMATTER=true` routes to existing Gemini path
- [x] Existing `validate_message`, `_truncate_to_fit`, `FormatterError` preserved
- [x] Tests cover: day abbreviation, condition abbreviation, prefix stripping, "then" handling, unknown fallback, truncation, full end-to-end format with real NWS fixtures
- [x] All existing tests still pass

## Owns

- `src/formatter.py` — add `DAY_MAP`, `CONDITION_MAP`, `_abbreviate_day()`, `_abbreviate_condition()`, `_strip_prefix()`, `_format_period()`, `_format_deterministic()`; modify `format_forecast()` to add env var dispatch
- `tests/test_formatter.py` — add deterministic formatter tests, keep existing validate_message tests

## Must not touch

- `src/nws_client.py` — no changes needed
- `src/email_poller.py` — unrelated
- `src/inreach_parser.py` — unrelated
- `src/reply_sender.py` — unrelated
- `src/main.py` — consumes `format_forecast` which keeps its interface
- `src/api.py` — consumes `format_forecast` which keeps its interface

## Defines interfaces

None — `format_forecast(command, periods) -> str` interface is unchanged.

## Pattern exemplar

- **Follow the pattern in**: `src/formatter.py` — existing module structure, `_truncate_to_fit` style, `FormatterError` usage

## Tasks

- [x] Add `DAY_MAP` dict and `_abbreviate_day(name)` function
- [x] Add `CONDITION_MAP` dict, prefix list, `_strip_prefix(forecast)`, `_abbreviate_condition(forecast)` with unknown fallback
- [x] Add `_format_period(period)` that assembles `DayCode CondCode Precip% Temp` token
- [x] Add `_format_deterministic(command, periods)` that joins periods and truncates
- [x] Modify `format_forecast` to check `USE_GEMINI_FORMATTER` env var and dispatch
- [x] Add unit tests for `_abbreviate_day` covering all NWS period name variants
- [x] Add unit tests for `_abbreviate_condition` covering known conditions, prefix stripping, "then" compounds, unknown fallback
- [x] Add end-to-end tests using real NWS fixture data (Seattle, NYC, Phoenix, Denver, Miami, Anchorage samples)
- [x] Verify all existing tests still pass

## Implementation notes

Real NWS fixture data was already collected during spec research. The 6 locations provide coverage of: rain/showers (Seattle), thunderstorms (NYC/Denver), clear/sunny (Phoenix/Miami), snow/mixed precip (Denver/Anchorage), fog conditions (not in samples but covered by lookup table).

The prefix stripping order matters — "Slight Chance" must be checked before "Chance" to avoid partial matches. Sort prefix list longest-first or use a regex alternation.

For the unknown fallback, multi-word: first letter of each word, padded to 3 chars. Single word: first 3 letters. Examples: "Volcanic Ash" → "VA\0" padded → "VA " or just "VA", "Sprinkles" → "Spr".
