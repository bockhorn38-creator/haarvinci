#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose up -d --wait db
uv run --frozen python manage.py migrate --check
uv run --frozen python scripts/backup.py backup --daily
exec uv run --frozen python scripts/serve.py
