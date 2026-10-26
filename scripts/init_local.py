"""Erzeugt nur fehlende lokale Konfiguration; bestehende Werte bleiben unangetastet."""

import os
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
local = ROOT / ".local"
local.mkdir(mode=0o700, exist_ok=True)
path = ROOT / ".env"
if not path.exists():
    content = (
        "DJANGO_DEBUG=true\n"
        f"DJANGO_SECRET_KEY={secrets.token_urlsafe(64)}\n"
        "DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,[::1]\n"
        "POSTGRES_DB=haarvinci\nPOSTGRES_USER=haarvinci\n"
        f"POSTGRES_PASSWORD={secrets.token_urlsafe(36)}\n"
        "POSTGRES_PORT=54329\n"
    )
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(content)
    print("Lokale Konfiguration angelegt (keine Geheimnisse im Repository).")
else:
    print("Vorhandene lokale Konfiguration wird beibehalten.")
