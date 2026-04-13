"""Gemini-based forecast formatter with validation and retry."""

import os
import re

from google import genai

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
# Prompt templates
# ---------------------------------------------------------------------------

_WX_NOW_PROMPT = """\
You are a weather formatter for satellite text messages limited to {max_len} characters.

Given forecast periods, produce a SINGLE LINE of abbreviated weather.
Rules:
- Maximum {max_len} characters total. Count carefully.
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
You are a weather formatter for satellite text messages limited to {max_len} characters.

Given forecast periods for the week, pack as many day/night entries as fit within {max_len} characters. Start from the first period and stop adding when the next entry would exceed the limit. Truncate from the end.

Rules:
- Maximum {max_len} characters total. Count carefully.
- Use abbreviated day names: Sun, Mon, Tue, Wed, Thu, Fri, Sat, Fr.
  Append "N" for night periods. Use "Td"/"Tn" for today/tonight.
- Use short condition codes: Clr, PCldy, MCldy, Cldy, RnShw, ChRn, Thnd, Snow, Fog, etc.
- Include precip % ONLY when > 0%.
- Always include the temperature number.
- No labels, no colons, no extra punctuation. Space-separated tokens.

Examples of good output:
Sun 74 TnClr57 Mon 80 Clr59 Tue 81 Clr60 Wed 85 Clr62 Thu 82 Clr59 Fr 80
Td 65 Tn48 Mon 72 Clr55 Tue 78 PCldy60 Wed 80 Clr58 Thu 75 MCldy52

Forecast periods:
{periods_text}

Output ONLY the formatted line, nothing else."""

_RETRY_SUFFIX = """

Your previous output was:
{previous}

That was {prev_len} chars, max is {max_len}. Remove periods from the END until it fits. Do NOT compress — just drop the last few day/night entries."""


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


def _get_client():
    """Configure and return the Gemini client."""
    return genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def format_forecast(command: str, periods: list) -> str:
    """Format forecast periods into a ≤160-char message using Gemini.

    Args:
        command: "wx now" or "wx week"
        periods: list of objects with name, temperature, precip_chance, short_forecast

    Returns:
        Formatted forecast string ≤160 characters.

    Raises:
        FormatterError: if all attempts fail validation.
    """
    client = _get_client()

    if command == "wx now":
        template = _WX_NOW_PROMPT
        periods = periods[:4]  # today, tonight, tomorrow, tomorrow night
    else:
        template = _WX_WEEK_PROMPT

    periods_text = _build_periods_text(periods)

    prompt = template.format(max_len=MAX_LEN, periods_text=periods_text)

    previous_output = None
    for attempt in range(MAX_ATTEMPTS):
        if previous_output is not None:
            full_prompt = prompt + _RETRY_SUFFIX.format(
                previous=previous_output,
                prev_len=len(previous_output),
                max_len=MAX_LEN,
            )
        else:
            full_prompt = prompt

        response = client.models.generate_content(
            model=GEMINI_MODEL, contents=full_prompt
        )
        message = re.sub(r"[^\x20-\x7E]", "", response.text.strip())

        # Hard truncate if over limit
        message = _truncate_to_fit(message)

        valid, reason = validate_message(message)
        if valid:
            return message

        previous_output = message

    raise FormatterError(
        f"Failed to get valid forecast after {MAX_ATTEMPTS} attempts. "
        f"Last output ({len(previous_output)} chars): {previous_output!r}. "
        f"Reason: {reason}"
    )
