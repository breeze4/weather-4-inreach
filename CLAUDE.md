# Weather Bot

## Commands

- **Test**: `python -m pytest tests/ -v`
- **Deploy**: `./deploy/deploy.sh`
- **Logs**: `ssh beebaby 'journalctl --user -u weather-bot -f'`
- **Status**: `ssh beebaby 'systemctl --user status weather-bot --no-pager -l'`
- **Restart**: `ssh beebaby 'systemctl --user restart weather-bot'`
- **Test API**: `curl 'http://beebaby:8035/forecast?lat=47.756259&lon=-122.350252'`

## Architecture

Single long-running process on beebaby with two responsibilities:
- IMAP poll loop (every 2 min) for InReach emails → NWS → Gemini → SMTP reply
- FastAPI test endpoint on port 8035 (runs in a daemon thread)
