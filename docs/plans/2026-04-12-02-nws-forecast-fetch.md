# NWS Forecast Fetch

## Parent spec

`docs/specs/2026-04-12-01-weather-bot-v1.md`

## What to build

A client module that takes lat/lon coordinates, calls the NWS API to get the 12-hourly forecast, and returns structured forecast period data. This is a thin wrapper around two NWS endpoints: `/points/{lat},{lon}` to get the forecast URL, then fetching that URL for the period data.

## Type

AFK

## Blocked by

None — can start immediately (develop with hardcoded test coordinates)

## User stories addressed

- User story 1 (24-hour forecast)
- User story 2 (multi-day forecast)

## Acceptance criteria

- [x] Calls NWS points API with lat/lon to get the forecast endpoint URL
- [x] Fetches 12-hourly forecast from the returned URL
- [x] Returns a list of forecast period objects (name, temperature, precip chance, short forecast text)
- [x] Raises a clear exception on API failure (network error, non-200 response, missing data)
- [x] Sets a proper User-Agent header (NWS requires identification)
- [ ] Can be called with test coordinates (e.g., 47.756259, -122.350252) and returns valid data

## Owns

- `src/nws_client.py` — NWS API calls, response parsing, forecast period dataclass

## Must not touch

- `src/email_poller.py` — owned by plan `2026-04-12-01-email-ingestion-parse.md`
- `src/inreach_parser.py` — owned by plan `2026-04-12-01-email-ingestion-parse.md`
- `src/formatter.py` — owned by plan `2026-04-12-03-gemini-formatter.md`
- `src/main.py` — owned by plan `2026-04-12-04-main-loop-reply-retry.md`

## Defines interfaces

- **Forecast period dataclass** (name, temperature, precip_chance, short_forecast) in `src/nws_client.py` — consumed by plans `2026-04-12-03`, `2026-04-12-04`
- **fetch_forecast function** in `src/nws_client.py` — consumed by plan `2026-04-12-04`

## Pattern exemplar

None — first of its kind. NWS API docs at https://www.weather.gov/documentation/services-web-api define the response shape.

## Tasks

- [x] Define forecast period dataclass (name, temperature, precip_chance, short_forecast)
- [x] Implement `fetch_forecast(lat, lon)`: call points API, extract forecast URL, fetch forecast, parse periods into dataclass list
- [x] Handle NWS error responses with clear exceptions
- [ ] Manual test with real coordinates to verify data shape

## Implementation notes

NWS API flow:
```
GET https://api.weather.gov/points/47.7563,-122.3503
  → response.properties.forecast = "https://api.weather.gov/gridpoints/SEW/124,69/forecast"

GET https://api.weather.gov/gridpoints/SEW/124,69/forecast
  → response.properties.periods = [
      { "name": "Today", "temperature": 62, "temperatureUnit": "F",
        "probabilityOfPrecipitation": {"value": 40},
        "shortForecast": "Chance Rain Showers" },
      ...
    ]
```

NWS requires a `User-Agent` header with contact info — use `(weather-bot, <GMAIL_USER>)`.

The `probabilityOfPrecipitation.value` may be `null` when there's no precip expected — treat null as 0%.
