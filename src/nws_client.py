"""NWS (National Weather Service) API client for fetching forecasts."""

import os
from dataclasses import dataclass

import requests

NWS_BASE = "https://api.weather.gov"
TIMEOUT = 15  # seconds


def _user_agent() -> str:
    return f"(weather-bot, {os.environ['GMAIL_USER']})"


class NWSError(Exception):
    """Raised when the NWS API returns an error or unexpected data."""


@dataclass
class ForecastPeriod:
    name: str
    temperature: int
    precip_chance: int  # 0-100
    short_forecast: str


def _get(url: str) -> dict:
    """Make a GET request to the NWS API and return parsed JSON."""
    headers = {"User-Agent": _user_agent(), "Accept": "application/geo+json"}
    try:
        resp = requests.get(url, headers=headers, timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise NWSError(f"Network error fetching {url}: {exc}") from exc

    if resp.status_code != 200:
        raise NWSError(
            f"NWS returned {resp.status_code} for {url}: {resp.text[:300]}"
        )

    try:
        return resp.json()
    except ValueError as exc:
        raise NWSError(f"Invalid JSON from {url}") from exc


def fetch_forecast(lat: float, lon: float) -> list[ForecastPeriod]:
    """Fetch the 12-hour-period forecast for the given coordinates.

    Makes two calls:
      1. /points/{lat},{lon} → gets the forecast grid URL
      2. That forecast URL → gets the period-level forecast

    Returns a list of ForecastPeriod dataclasses.
    Raises NWSError on any failure.
    """
    # NWS wants max 4 decimal places for coordinates.
    points_url = f"{NWS_BASE}/points/{lat:.4f},{lon:.4f}"
    points_data = _get(points_url)

    try:
        forecast_url = points_data["properties"]["forecast"]
    except (KeyError, TypeError) as exc:
        raise NWSError(
            f"Missing forecast URL in /points response for ({lat}, {lon})"
        ) from exc

    if not forecast_url:
        raise NWSError(f"Empty forecast URL in /points response for ({lat}, {lon})")

    forecast_data = _get(forecast_url)

    try:
        periods_raw = forecast_data["properties"]["periods"]
    except (KeyError, TypeError) as exc:
        raise NWSError("Missing periods in forecast response") from exc

    if not periods_raw:
        raise NWSError("Empty periods list in forecast response")

    periods: list[ForecastPeriod] = []
    for p in periods_raw:
        try:
            # probabilityOfPrecipitation.value can be null → treat as 0
            pop = p.get("probabilityOfPrecipitation") or {}
            precip = pop.get("value")
            if precip is None:
                precip = 0

            periods.append(
                ForecastPeriod(
                    name=p["name"],
                    temperature=int(p["temperature"]),
                    precip_chance=int(precip),
                    short_forecast=p["shortForecast"],
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise NWSError(f"Malformed period data: {exc}") from exc

    return periods
