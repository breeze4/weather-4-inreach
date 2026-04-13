"""Forecast formatter with deterministic and Gemini-based paths."""

import os
import re

GEMINI_MODEL = "gemini-3.1-flash-lite-preview"
MAX_LEN = 160
MAX_ATTEMPTS = 3

DAY_PATTERN = re.compile(
    r"\b(Mon|Tue|Wed|Thu|Fri|Sat|Sun|Td|Tn|"
    r"MonN|TueN|WedN|ThuN|FriN|SatN|SunN|Fr)\b",
    re.IGNORECASE,
)
TEMP_PATTERN = re.compile(r"\d{2,3}")


class FormatterError(Exception):
    """Raised when Gemini fails to produce a valid formatted forecast."""


def validate_message(message: str) -> tuple[bool, str]:
    """Check that a formatted forecast message meets all constraints.

    Returns (is_valid, reason) where reason describes the first failure.
    """
    if len(message) > MAX_LEN:
        return False, f"Too long: {len(message)} chars (max {MAX_LEN})"
    if not TEMP_PATTERN.search(message):
        return False, "No temperature number found"
    if not DAY_PATTERN.search(message):
        return False, "No day abbreviation found"
    return True, ""


# ---------------------------------------------------------------------------
# Deterministic formatter
# ---------------------------------------------------------------------------

DAY_MAP = {
    "today": "Td",
    "this afternoon": "Td",
    "tonight": "Tn",
    "sunday": "Sun",
    "monday": "Mon",
    "tuesday": "Tue",
    "wednesday": "Wed",
    "thursday": "Thu",
    "friday": "Fri",
    "saturday": "Sat",
    "sunday night": "SunN",
    "monday night": "MonN",
    "tuesday night": "TueN",
    "wednesday night": "WedN",
    "thursday night": "ThuN",
    "friday night": "FriN",
    "saturday night": "SatN",
}

CONDITION_MAP = {
    # Sky
    "sunny": "Sun",
    "mostly sunny": "MSun",
    "partly sunny": "PSun",
    "clear": "Clr",
    "mostly clear": "MClr",
    "partly cloudy": "PCldy",
    "mostly cloudy": "MCldy",
    "cloudy": "Cldy",
    # Rain
    "rain": "Rn",
    "light rain": "LRn",
    "heavy rain": "HRn",
    "showers": "Shw",
    "rain showers": "RnShw",
    "drizzle": "Dzl",
    # Snow/ice
    "snow": "Snw",
    "light snow": "LSnw",
    "heavy snow": "HSnw",
    "snow showers": "SnShw",
    "flurries": "Flr",
    "sleet": "Slt",
    "wintry mix": "WMx",
    "rain and snow": "RnSn",
    "rain and snow showers": "RnSnShw",
    # Freezing
    "freezing rain": "FzRn",
    "freezing drizzle": "FzDzl",
    "freezing fog": "FzFg",
    "freezing spray": "FzSp",
    # Thunderstorms
    "thunderstorms": "Tst",
    "showers and thunderstorms": "ShTst",
    "t-storms": "Tst",
    "severe t-storms": "SvTst",
    # Visibility
    "fog": "Fog",
    "dense fog": "DFog",
    "ice fog": "IFg",
    "haze": "Hze",
    "smoke": "Smk",
    "blowing snow": "BlSn",
    "blowing dust": "BlDt",
    "frost": "Frs",
    # Wind/temp
    "breezy": "Brz",
    "windy": "Wnd",
    "very windy": "VWnd",
    "blustery": "Bls",
    "hot": "Hot",
    "cold": "Cld",
    "damaging winds": "DmgW",
}

_PREFIXES = sorted(
    [
        "slight chance",
        "chance",
        "likely",
        "isolated",
        "scattered",
        "numerous",
        "areas",
        "patchy",
    ],
    key=len,
    reverse=True,
)


def _abbreviate_day(name: str) -> str:
    """Map an NWS period name to a short day code."""
    return DAY_MAP.get(name.lower(), name)


def _strip_prefix(forecast: str) -> str:
    """Strip probability/coverage prefixes from a forecast string."""
    lower = forecast.lower()
    for prefix in _PREFIXES:
        if lower.startswith(prefix + " "):
            return forecast[len(prefix) + 1:]
    return forecast


def _abbreviate_condition(forecast: str) -> str:
    """Abbreviate an NWS short_forecast string to a condition code."""
    # Handle compound "then" forecasts — take first part only
    if " then " in forecast.lower():
        forecast = forecast[:forecast.lower().index(" then ")]

    # Strip probability prefix
    forecast = _strip_prefix(forecast)

    # Lookup in condition map (case-insensitive)
    key = forecast.strip().lower()
    if key in CONDITION_MAP:
        return CONDITION_MAP[key]

    # Unknown fallback
    words = forecast.strip().split()
    if len(words) > 1:
        return "".join(w[0].upper() for w in words)
    else:
        return forecast.strip()[:3].capitalize()


def _format_period(period) -> str:
    """Format a single ForecastPeriod into space-separated tokens.

    Format: DayCode CondCode Precip% Temp
    """
    day = _abbreviate_day(period.name)
    cond = _abbreviate_condition(period.short_forecast)
    parts = [day, cond]
    if period.precip_chance > 0:
        parts.append(f"{period.precip_chance}%")
    parts.append(str(period.temperature))
    return " ".join(parts)


def _format_deterministic(command: str, periods: list) -> str:
    """Format forecast periods deterministically without LLM calls."""
    if command == "wx now":
        periods = periods[:4]

    tokens = [_format_period(p) for p in periods]
    message = " ".join(tokens)
    return _truncate_to_fit(message)


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_WX_NOW_PROMPT = """\
You are a weather formatter for satellite text messages.

Given forecast periods, produce a SINGLE LINE of abbreviated weather.
Rules:
- Use abbreviated day names: Sun, Mon, Tue, Wed, Thu, Fri, Sat.
  Use "Td" for today, "Tn" for tonight. Append "N" for night periods (e.g. WedN).
- Use short condition codes: Clr, PCldy, MCldy, Cldy, RnShw, ChRn, Thnd, Snow, Fog, etc.
- Include precip % ONLY when > 0%. Format: CondCode XX%
- Always include the temperature number.
- No labels, no colons, no extra punctuation. Just space-separated tokens.

Examples of good output:
Td Sun 74 Tn Clr 57 Wed PCldy 68 WedN Clr 52
Td RnShw 58% 57 Tn RnShw 39% 41 Wed ChRn 40% 55 WedN MCldy 18% 43
Sun PCldy 65 SunN Clr 48 Mon Clr 72 MonN Clr 55

Forecast periods:
{periods_text}

Output ONLY the formatted line, nothing else."""

_WX_WEEK_PROMPT = """\
You are a weather formatter for satellite text messages.

Given forecast periods for the week, format ALL periods into a single line.
The output will be truncated by the app if needed — just format everything.

Rules:
- Use abbreviated day names: Sun, Mon, Tue, Wed, Thu, Fri, Sat.
  Append "N" for night periods. Use "Td"/"Tn" for today/tonight.
- Use short condition codes: Clr, PCldy, MCldy, Cldy, RnShw, ChRn, Thnd, Snow, Fog, etc.
- Include precip % ONLY when > 0%.
- Always include the temperature number.
- No labels, no colons, no extra punctuation. Space-separated tokens.

Examples of good output:
Sun 74 SunN Clr 57 Mon 80 MonN Clr 59 Tue 81 TueN Clr 60 Wed 85 WedN Clr 62
Td 65 Tn 48 Mon 72 MonN Clr 55 Tue PCldy 78 TueN 60 Wed 80 WedN Clr 58

Forecast periods:
{periods_text}

Output ONLY the formatted line, nothing else."""


def _build_periods_text(periods: list) -> str:
    """Turn period objects into a readable block for the prompt."""
    lines = []
    for p in periods:
        precip = f", precip {p.precip_chance}%" if p.precip_chance > 0 else ""
        lines.append(f"- {p.name}: {p.temperature}°F, {p.short_forecast}{precip}")
    return "\n".join(lines)


def _truncate_to_fit(message: str) -> str:
    """Truncate a space-separated forecast at the last token that fits in MAX_LEN."""
    if len(message) <= MAX_LEN:
        return message
    cut = message[:MAX_LEN]
    # Walk back to the last space to avoid splitting a token
    last_space = cut.rfind(" ")
    if last_space > 0:
        cut = cut[:last_space]
    return cut.rstrip()


def _get_client(genai=None):
    """Configure and return the Gemini client."""
    if genai is None:
        from google import genai as _genai
        genai = _genai
    return genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def format_forecast(command: str, periods: list) -> str:
    """Format forecast periods into a ≤160-char message.

    Uses deterministic formatting by default. Set USE_GEMINI_FORMATTER=true
    to use the Gemini-based formatter instead.

    Args:
        command: "wx now" or "wx week"
        periods: list of objects with name, temperature, precip_chance, short_forecast

    Returns:
        Formatted forecast string ≤160 characters.

    Raises:
        FormatterError: if all attempts fail validation (Gemini path only).
    """
    if os.environ.get("USE_GEMINI_FORMATTER") != "true":
        return _format_deterministic(command, periods)

    from google import genai  # noqa: F811

    client = _get_client(genai)

    if command == "wx now":
        template = _WX_NOW_PROMPT
        periods = periods[:4]  # today, tonight, tomorrow, tomorrow night
    else:
        template = _WX_WEEK_PROMPT

    periods_text = _build_periods_text(periods)

    prompt = template.format(periods_text=periods_text)

    last_output = None
    last_reason = None
    for attempt in range(MAX_ATTEMPTS):
        response = client.models.generate_content(
            model=GEMINI_MODEL, contents=prompt
        )
        message = re.sub(r"[^\x20-\x7E]", "", response.text.strip())

        # App-side truncation to fit the 160-char limit
        message = _truncate_to_fit(message)

        valid, reason = validate_message(message)
        if valid:
            return message

        last_output = message
        last_reason = reason

    raise FormatterError(
        f"Failed to get valid forecast after {MAX_ATTEMPTS} attempts. "
        f"Last output ({len(last_output)} chars): {last_output!r}. "
        f"Reason: {last_reason}"
    )
