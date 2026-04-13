"""Test API for weather-bot. Returns formatted forecasts as JSON."""

import os

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException

from src.formatter import format_forecast, FormatterError
from src.nws_client import fetch_forecast, NWSError

app = FastAPI(title="Weather Bot API")


@app.get("/forecast")
def forecast(lat: float, lon: float):
    """Fetch and format forecast for both wx now and wx week."""
    try:
        periods = fetch_forecast(lat, lon)
    except NWSError as exc:
        raise HTTPException(status_code=502, detail=f"NWS error: {exc}")

    results = {}
    for command in ("wx now", "wx week"):
        try:
            results[command] = format_forecast(command, periods)
        except FormatterError as exc:
            results[command] = f"error: {exc}"

    return {
        "lat": lat,
        "lon": lon,
        "periods": len(periods),
        "wx_now": results["wx now"],
        "wx_week": results["wx week"],
    }
