#!/usr/bin/env bash
# Deploy weather-bot to beebaby from dev machine.
# Usage: ./deploy/deploy.sh
set -euo pipefail

HOST=beebaby
APP_DIR=dev/weather-bot
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "==> Syncing code to $HOST:~/$APP_DIR"
rsync -az --delete \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='venv' \
  --exclude='*.pyc' \
  --exclude='.env' \
  --exclude='.pytest_cache' \
  "$PROJECT_DIR/" "$HOST:$APP_DIR/"

echo "==> Installing Python deps"
ssh "$HOST" "cd ~/$APP_DIR && venv/bin/pip install -q -r requirements.txt"

echo "==> Installing user systemd service"
ssh "$HOST" "mkdir -p ~/.config/systemd/user && cp ~/$APP_DIR/deploy/weather-bot.service ~/.config/systemd/user/ && systemctl --user daemon-reload"

echo "==> Restarting service"
ssh "$HOST" "systemctl --user restart weather-bot"

echo "==> Done. Status:"
ssh "$HOST" "systemctl --user status weather-bot --no-pager -l" || true
