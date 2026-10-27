import os
from pathlib import Path
from urllib.parse import quote

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

from .base_settings import *  # noqa: F403
from .base_settings import INSTALLED_APPS

INSTALLED_APPS = [*INSTALLED_APPS, "google_broker"]

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
DEBUG = os.getenv("DJANGO_DEBUG", "false").lower() == "true"
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "")
if len(SECRET_KEY) < 50:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY muss mindestens 50 Zeichen haben.")
ALLOWED_HOSTS = [
    h.strip()
    for h in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]").split(",")
    if h.strip()
]
if not DEBUG and (not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS):
    raise ImproperlyConfigured("Für Produktion explizite DJANGO_ALLOWED_HOSTS setzen.")
CSRF_TRUSTED_ORIGINS = [h for h in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if h]

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    password = os.getenv("POSTGRES_PASSWORD", "")
    if not password:
        raise ImproperlyConfigured("DATABASE_URL oder POSTGRES_PASSWORD fehlt.")
    DATABASE_URL = "postgresql://{}:{}@{}:{}/{}".format(
        quote(os.getenv("POSTGRES_USER", "haarvinci"), safe=""),
        quote(password, safe=""),
        os.getenv("POSTGRES_HOST", "127.0.0.1"),
        os.getenv("POSTGRES_PORT", "54329"),
        quote(os.getenv("POSTGRES_DB", "haarvinci"), safe=""),
    )
DATABASES = {
    "default": dj_database_url.parse(DATABASE_URL, conn_max_age=60, conn_health_checks=True)
}
if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
    raise ImproperlyConfigured("Haarvinci benötigt PostgreSQL.")

SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"
# Kein blindes Vertrauen in vom Client gesendete Proxy-Header.
# Ein HTTPS-Reverse-Proxy muss X-Forwarded-Proto überschreiben, siehe docs/BETRIEB.md.
if os.getenv("DJANGO_TRUST_PROXY", "false").lower() == "true":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
