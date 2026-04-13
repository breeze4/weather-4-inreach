# Deterministic NWS Forecast Formatter

## Problem

The current formatter sends NWS forecast data to Gemini to produce abbreviated satellite messages. This adds latency, cost, a runtime dependency on an external LLM API, and nondeterministic output that's hard to test. The NWS `shortForecast` vocabulary is finite and well-documented enough to abbreviate deterministically.

## Solution

Replace the Gemini-based formatter with a deterministic parser that abbreviates NWS period names, condition strings, and precipitation into space-separated tokens that fit the 160-char InReach message limit. Keep the Gemini path available behind an env var for comparison/fallback.

## Data Flow

1. `format_forecast(command, periods)` receives `ForecastPeriod` objects (name, temperature, precip_chance, short_forecast)
2. For each period:
   a. Abbreviate `name` → day code (e.g. "Monday Night" → "MonN", "Tonight" → "Tn")
   b. Abbreviate `short_forecast` → condition code (e.g. "Mostly Cloudy" → "MCldy")
   c. Assemble token: `DayCode CondCode Precip% Temp`
3. Join all period tokens with spaces
4. Truncate at last complete token boundary to fit 160 chars
5. Return the string

## Behavior

### Day Name Abbreviation

| NWS Name | Code |
|---|---|
| Today | Td |
| Tonight | Tn |
| This Afternoon | Td |
| Sunday / Monday / ... / Saturday | Sun / Mon / Tue / Wed / Thu / Fri / Sat |
| Sunday Night / Monday Night / ... | SunN / MonN / TueN / WedN / ThuN / FriN / SatN |

### Condition Abbreviation

Map the core weather condition (after stripping probability prefixes and "then" transitions) to a short code. The lookup table covers the known NWS vocabulary:

**Sky conditions:** Sunny → Sun, Mostly Sunny → MSun, Partly Sunny → PSun, Clear → Clr, Mostly Clear → MClr, Partly Cloudy → PCldy, Mostly Cloudy → MCldy, Cloudy → Cldy

**Rain:** Rain → Rn, Light Rain → LRn, Heavy Rain → HRn, Showers → Shw, Rain Showers → RnShw, Drizzle → Dzl

**Snow/ice:** Snow → Snw, Light Snow → LSnw, Heavy Snow → HSnw, Snow Showers → SnShw, Flurries → Flr, Sleet → Slt, Wintry Mix → WMx, Rain And Snow → RnSn, Rain And Snow Showers → RnSnShw

**Freezing:** Freezing Rain → FzRn, Freezing Drizzle → FzDzl, Freezing Fog → FzFg, Freezing Spray → FzSp

**Thunderstorms:** Thunderstorms → Tst, Showers And Thunderstorms → ShTst, T-storms → Tst, Severe T-storms → SvTst

**Visibility:** Fog → Fog, Dense Fog → DFog, Ice Fog → IFg, Haze → Hze, Smoke → Smk, Blowing Snow → BlSn, Blowing Dust → BlDt, Frost → Frs

**Wind/temp:** Breezy → Brz, Windy → Wnd, Very Windy → VWnd, Blustery → Bls, Hot → Hot, Cold → Cld, Damaging Winds → DmgW

**Tropical:** Handled as passthrough via unknown fallback.

### Probability Prefix Handling

NWS prepends "Slight Chance", "Chance", "Likely", "Isolated", "Scattered", "Numerous", "Areas", "Patchy" to weather types. These are **stripped** before condition lookup — the precip_chance percentage already conveys probability.

### Compound Forecasts ("then")

When `shortForecast` contains "then" (e.g. "Partly Sunny then Slight Chance Rain Showers"), take **only the first part** before "then".

### Unknown Condition Fallback

If a condition string doesn't match the lookup table after prefix stripping, generate a 3-character abbreviation: first letter of each word (e.g. "Volcanic Ash" → "VA", pad to 3 if needed). Single words: first 3 letters.

### Token Format Per Period

```
DayCode CondCode Precip% Temp
```

- `CondCode` always included
- `Precip%` only when precip_chance > 0, formatted as integer with % suffix (e.g. `70%`)
- `Temp` always included, bare integer

Example: `MonN Rn 75% 44`

### wx now vs wx week

- `wx now`: first 4 periods (today, tonight, tomorrow, tomorrow night)
- `wx week`: all periods, truncated at token boundary to fit 160 chars

### Truncation

Same as current: if the assembled string exceeds 160 chars, cut at the last space before the limit. This means `wx week` gracefully drops trailing periods.

### Env Var Switch

`USE_GEMINI_FORMATTER=true` routes to the existing Gemini path. Any other value or unset defaults to the deterministic parser. The Gemini code stays in the module but is not the default path.

## Modules

### `src/formatter.py` — modify

- Add condition lookup table (`CONDITION_MAP`), day name lookup table (`DAY_MAP`), prefix stripping logic, unknown fallback, and `_format_deterministic(command, periods)` function
- `format_forecast` checks `USE_GEMINI_FORMATTER` env var and dispatches
- Keep existing Gemini path intact, `validate_message`, `_truncate_to_fit`, `FormatterError`
- Remove `_build_periods_text` (only used by Gemini prompts, keep if Gemini path stays)

### `tests/test_formatter.py` — modify

- Test the deterministic formatter against real NWS response fixtures from multiple locations
- Test each component: day abbreviation, condition abbreviation, prefix stripping, "then" handling, unknown fallback, truncation, full format_forecast output
- Existing validate_message tests stay

### Test Fixtures

Capture real NWS API responses as test data: the 6 locations already sampled (Seattle, NYC, Phoenix, Denver, Miami, Anchorage) give good coverage of rain, snow, thunderstorms, clear skies, mixed precip, and fog conditions.

## Judgment Calls

- **Strip probability prefixes entirely** rather than abbreviating them. The `precip_chance` field already has the number, and "Slight Chance" vs "Chance" vs "Likely" are just probability brackets that would waste chars.
- **First part of "then" compounds only.** Saves space, and the primary condition is more useful than the transition.
- **3-char fallback for unknowns** is acceptable data loss for edge cases like tropical conditions that are rare for the target use case (backcountry hiking).
- **Env var switch, not config file.** Consistent with how the rest of the app is configured.
