#!/usr/bin/env bash
set -euo pipefail
umask 077
cd "$(dirname "$0")/.."
command -v uv >/dev/null || { echo "Bitte zuerst uv installieren: https://docs.astral.sh/uv/"; exit 1; }
command -v docker >/dev/null || { echo "Bitte Docker mit Compose installieren."; exit 1; }
python3 scripts/init_local.py
uv sync --frozen
docker compose up -d --wait db
uv run --frozen python manage.py migrate --noinput
uv run --frozen python manage.py check
uv run --frozen python manage.py collectstatic --noinput
# Demo ist ein ausdrücklicher separater Schritt; das Setup verändert keine Kundenakten.
echo "Einrichtung abgeschlossen. Für fiktive Beispieldaten: uv run python manage.py init_demo"
