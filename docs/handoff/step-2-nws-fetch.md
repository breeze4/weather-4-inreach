# Step 2 Handoff: NWS Forecast Fetch

## Files created

- `src/nws_client.py`

## Dataclass: ForecastPeriod

| Field            | Type  | Notes              |
|------------------|-------|--------------------|
| `name`           | `str` | e.g. "Today", "Tonight" |
| `temperature`    | `int` | degrees (unit from NWS, typically F) |
| `precip_chance`  | `int` | 0-100; null from API treated as 0 |
| `short_forecast` | `str` | e.g. "Chance Rain Showers" |

## Function signature

```python
def fetch_forecast(lat: float, lon: float) -> list[ForecastPeriod]
```

Raises `NWSError` (subclass of `Exception`) on any failure.

## NWS API quirks

- `probabilityOfPrecipitation.value` is `null` (not 0) when no precipitation is expected. Code defaults this to 0.
- NWS requires a `User-Agent` header with contact info or requests may be rejected.
- Coordinates are truncated to 4 decimal places (NWS precision limit).
- Two sequential HTTP calls are required: `/points/{lat},{lon}` to discover the forecast grid URL, then that URL for the actual forecast data.
- The `Accept: application/geo+json` header is set per NWS documentation.
