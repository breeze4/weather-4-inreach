# Weather Bot

Self-hosted weather forecast service for Garmin InReach satellite messengers. Send `wx now` or `wx week` from your InReach and get a formatted NWS forecast back on the device.

Replaces the defunct wx2inreach.com service.

## How it works

1. InReach sends a message to a dedicated Gmail address
2. Bot polls Gmail via IMAP, parses the command and GPS coordinates
3. Fetches forecast from the NWS API for those coordinates
4. Gemini Flash compresses the forecast into a ≤160 character satellite message
5. Replies via the Garmin MapShare reply page (the only way to deliver messages back to InReach)

## Commands

- **`wx now`** — 24-hour forecast: today, tonight, tomorrow, tomorrow night with temps, precip %, and conditions
- **`wx week`** — 7-day forecast: as many day/night periods as fit in 160 chars, truncated from the end

## Example output

```
wx now:  Td PCldy 15% 60 Tn Rn 70% 47 Mon Rn 59% 52 MonN Rn 75% 44
wx week: Tn47 LtRn70 Mon 52 LtRn59 MonN 44 LtRn75 Tue 49 Rn99 TueN 39 Rn95 Wed 51 Thnd84
```

## Setup

```bash
# Clone and configure
cp .env.example .env
# Edit .env with your credentials

# Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run tests
python -m pytest tests/ -v

# Run locally
python -m src.main
```

## Environment variables

| Variable | Description |
|---|---|
| `GMAIL_USER` | Gmail address the bot polls (e.g. `your_email@gmail.com`) |
| `GMAIL_APP_PASSWORD` | Gmail App Password for IMAP/SMTP access |
| `GEMINI_API_KEY` | Google Gemini API key |
| `INREACH_EMAIL` | InReach device email (e.g. `user@inreach.garmin.com`) |

## Deploy to a server

```bash
# One-time setup on the server
ssh yourserver 'bash -s' < deploy/setup.sh

# Copy your .env to the server
scp .env yourserver:~/dev/weather-bot/.env

# Deploy (rsync + restart service)
./deploy/deploy.sh
```

## Test API

The bot runs a test API on port 8035:

```
GET /forecast?lat=47.756&lon=-122.350
```

Returns JSON with `wx_now` and `wx_week` formatted forecasts.

## Architecture

Single long-running Python process with two threads:

- **Main thread**: IMAP poll loop (every 2 min) — parse email, fetch NWS, format via Gemini, reply via Garmin
- **Daemon thread**: FastAPI test endpoint on port 8035

NWS failures trigger automatic retries every 2 minutes for up to 20 minutes.
