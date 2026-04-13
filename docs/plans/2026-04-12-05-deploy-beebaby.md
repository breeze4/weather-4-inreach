# Deploy to beebaby

## Parent spec

`docs/specs/2026-04-12-01-weather-bot-v1.md`

## What to build

Deployment scaffolding for beebaby: systemd user service, deploy script, setup script, and `.env` file. The service runs the main loop as a long-running process that starts on boot and restarts on crash. Same deployment model works on a GCP e2-micro later.

## Type

HITL — user needs to fill in `.env` secrets and run the first deploy manually

## Blocked by

- Blocked by `2026-04-12-04-main-loop-reply-retry.md`

## User stories addressed

- User story 8 (runs unattended on beebaby)

## Acceptance criteria

- [ ] `deploy/weather-bot.service` systemd user unit runs `main.py` as a long-running service
- [ ] Service restarts on crash (`Restart=always`)
- [ ] Service loads `.env` via `EnvironmentFile`
- [ ] `deploy/setup.sh` creates app directory and enables linger
- [ ] `deploy/deploy.sh` rsyncs code, installs deps, restarts service
- [ ] `.env` file is deployed alongside the code (excluded from git)
- [ ] `.gitignore` excludes `.env` but not `.env.example`
- [ ] `requirements.txt` lists all Python dependencies
- [ ] Service starts successfully on beebaby and processes a test email

## Owns

- `deploy/weather-bot.service` — systemd user unit
- `deploy/deploy.sh` — rsync + restart deploy script
- `deploy/setup.sh` — one-time server setup
- `.env` — runtime secrets (not committed)
- `.env.example` — template (committed)
- `.gitignore`
- `requirements.txt`

## Must not touch

- `src/` — all source files owned by earlier plans

## Defines interfaces

None

## Pattern exemplar

- **MUST follow the pattern in**: `~/dev/hiking-food/deploy/` — systemd user service + rsync deploy for a Python app on beebaby

## Tasks

- [ ] Create `requirements.txt` with dependencies: `google-generativeai` (or equivalent Gemini client), `python-dotenv`
- [ ] Create `.gitignore`: exclude `.env`, `__pycache__`, `venv`, `*.pyc`
- [ ] Create `.env.example` with all required vars: `GMAIL_USER`, `GMAIL_APP_PASSWORD`, `GEMINI_API_KEY`, `INREACH_EMAIL`
- [ ] Create `deploy/weather-bot.service` following beebaby pattern: `ExecStart` runs Python with `src/main.py`, `EnvironmentFile` points to `.env`, `Restart=always`
- [ ] Create `deploy/setup.sh`: mkdir app dir, create venv, enable linger
- [ ] Create `deploy/deploy.sh`: rsync code, install deps in venv, copy service file, daemon-reload, restart
- [ ] User fills in `.env` with real credentials
- [ ] Run `deploy/setup.sh` on beebaby
- [ ] Run `deploy/deploy.sh` from dev machine
- [ ] Verify service is running: `systemctl --user status weather-bot`
- [ ] Send test `wx now` from InReach and verify reply arrives
