"""Eigenständige Windows-App: gleicher Fachkern, lokaler SQLite-Datenspeicher."""

import os
from pathlib import Path

from .base_settings import *  # noqa: F403
from .base_settings import INSTALLED_APPS, MIDDLEWARE

DESKTOP_MODE = True
DEBUG = False
SECRET_KEY = os.environ["HAARVINCI_DESKTOP_SECRET"]
DESKTOP_TOKEN = os.environ["HAARVINCI_DESKTOP_TOKEN"]
DATA_DIR = Path(os.environ["HAARVINCI_DATA_DIR"])
ALLOWED_HOSTS = ["127.0.0.1"]
CSRF_TRUSTED_ORIGINS = []
INSTALLED_APPS = [*INSTALLED_APPS, "desktop_app"]
MIDDLEWARE = ["desktop_app.middleware.DesktopGateMiddleware", *MIDDLEWARE]
ROOT_URLCONF = "desktop_app.urls"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DATA_DIR / "haarvinci.sqlite3",
        # Frühe Schreibsperre schützt auch optimistische Änderungen bei parallelen Requests.
        "OPTIONS": {"timeout": 30, "transaction_mode": "IMMEDIATE"},
    }
}
SESSION_COOKIE_NAME = "haarvinci_desktop_session"
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    # Lokale Dateien aus dem signierten/prüfbaren Programmpaket, kein Build zur Laufzeit.
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = True
