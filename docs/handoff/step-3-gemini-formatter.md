# Step 3: Gemini Formatter — Handoff

## Files created

- `src/formatter.py` — Gemini API call, prompt templates, validation, retry loop
- `tests/test_formatter.py` — 8 validation unit tests (all passing)

## Function signature

```python
format_forecast(command: str, periods: list) -> str
```

- `command`: `"wx now"` or `"wx week"`
- `periods`: list of objects with `.name` (str), `.temperature` (int), `.precip_chance` (int 0-100), `.short_forecast` (str)
- Returns: formatted string ≤160 characters
- Raises: `FormatterError` if all 3 attempts fail validation

Also exported: `validate_message(message: str) -> tuple[bool, str]` and `FormatterError`.

## Gemini model

Uses `gemini-2.0-flash` via `google.generativeai`. API key read from `os.environ["GEMINI_API_KEY"]`.

Note: `GEMINI_API_KEY` was NOT added to `.env.example` per instructions. It must be set in the environment.

## Prompt templates

Two templates, one per command type:

- **wx now**: Instructs Gemini to produce abbreviated day/night periods with condition codes and temperatures. Precip % included only when > 0%. Three examples provided.
- **wx week**: Same format but instructs Gemini to pack as many periods as fit within 160 chars, truncating from the end. Two examples provided.

On retry, appends: "Your previous output was: {output}. That was {len} chars, max is 160. Shorten it while keeping the same format."

## Validation rules

1. `len(message) <= 160`
2. Contains at least one 2-3 digit temperature number (`\d{2,3}`)
3. Contains at least one day abbreviation (Mon, Tue, Wed, Thu, Fri, Sat, Sun, Td, Tn, Fr, or night variants like WedN)

## Known issues

- The `google.generativeai` package is deprecated in favor of `google.genai`. A FutureWarning is emitted on import. Consider migrating to the new package if this causes problems.
- Gemini output quality has not been tested with real NWS data yet (no API key available in this context). The prompts include explicit examples and constraints which should produce good results, but may need tuning after live testing.
