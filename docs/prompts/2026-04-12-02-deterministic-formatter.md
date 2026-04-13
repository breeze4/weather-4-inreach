# Orchestration Prompt: Deterministic NWS Formatter

## Project context

- Working directory: `/home/breeze/dev/weather-bot`
- Test: `python -m pytest tests/ -v`
- Spec: `docs/specs/2026-04-12-02-deterministic-formatter.md`

## Orchestrator responsibilities

Before launching the agent:

1. Read `docs/specs/2026-04-12-02-deterministic-formatter.md` and `docs/plans/2026-04-12-06-deterministic-formatter.md`
2. Read `src/formatter.py` and `tests/test_formatter.py` — paste their full contents into the agent's "Context" field
3. Read `src/nws_client.py` lines 21-26 (the `ForecastPeriod` dataclass) — paste into Context so the agent knows the input shape

## Execution plan

### Step 1 — Deterministic NWS formatter with tests

**Plan**: `docs/plans/2026-04-12-06-deterministic-formatter.md`

**Agent briefing**:
- **Context sources** (orchestrator reads these): `docs/specs/2026-04-12-02-deterministic-formatter.md`, `src/formatter.py`, `tests/test_formatter.py`, `src/nws_client.py` (ForecastPeriod dataclass only)
- **Read first**: `docs/plans/2026-04-12-06-deterministic-formatter.md`
- **Context**: <orchestrator pastes spec, current formatter.py, current test_formatter.py, and ForecastPeriod dataclass here>
- **Owns**: `src/formatter.py`, `tests/test_formatter.py`
- **Must not touch**: `src/nws_client.py`, `src/email_poller.py`, `src/inreach_parser.py`, `src/reply_sender.py`, `src/main.py`, `src/api.py`, `tests/test_inreach_parser.py`, `tests/test_retry_manager.py`
- **Follow the pattern in**: `src/formatter.py` — existing module structure, keep `_truncate_to_fit`, `validate_message`, `FormatterError` intact
- **Do not**: modify the `format_forecast(command, periods) -> str` public interface. Callers in `src/main.py` and `src/api.py` must not need changes.
- **Do not**: remove the Gemini code path. It stays, gated behind `USE_GEMINI_FORMATTER=true`.
- **Done when**: `python -m pytest tests/ -v` passes with all new deterministic formatter tests AND all existing validate_message/inreach_parser/retry_manager tests. The deterministic path produces correct output for all 6 location fixtures.

**Implementation guidance**:

The prefix stripping order matters. These prefixes must be checked longest-first to avoid partial matches:
```
Slight Chance, Chance, Likely, Isolated, Scattered, Numerous, Areas, Patchy
```

For end-to-end test fixtures, use real NWS data. Here are the periods collected from 6 US locations (orchestrator: paste these into context or have the agent fetch fresh ones):

- **Seattle** (47.7563, -122.3503): rain, light rain, showers and thunderstorms
- **NYC** (40.7128, -74.0060): mostly cloudy, slight chance rain showers, chance showers and thunderstorms
- **Phoenix** (33.4484, -112.0740): sunny, clear, partly cloudy, slight chance rain showers
- **Denver** (39.7392, -104.9903): rain showers, rain and snow showers, chance snow showers
- **Miami** (25.7617, -80.1918): mostly sunny, mostly clear, partly cloudy
- **Anchorage** (61.2181, -149.9003): rain and snow, chance light snow, chance rain and snow

Each fixture should be a list of `ForecastPeriod` objects with the real name/temperature/precip_chance/short_forecast values. Test that `_format_deterministic("wx now", periods[:4])` and `_format_deterministic("wx week", periods)` produce valid output (passes `validate_message`, correct day codes, correct condition codes, respects 160-char limit for wx week).

Stay within your plan's scope. Do not refactor callers or unrelated modules.

**Gate**: `python -m pytest tests/ -v` — all tests pass (existing + new).

## Completion criteria

- All plan acceptance criteria met (see plan file)
- `python -m pytest tests/ -v` passes
- Deterministic formatter is the default path (no env var needed)
- `USE_GEMINI_FORMATTER=true` still routes to Gemini path
