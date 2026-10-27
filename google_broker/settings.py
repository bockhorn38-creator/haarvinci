"""Unabhängig zu betreibender, optionaler HTTPS-Anmeldedienst; nie auf Android laden."""

import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get("GOOGLE_BROKER_DJANGO_SECRET", "")
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_HANDOFF_KEY = os.environ.get("GOOGLE_HANDOFF_KEY", "")
GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "")
if len(SECRET_KEY) < 50 or not all(
    [
        GOOGLE_CLIENT_ID,
        GOOGLE_CLIENT_SECRET,
        GOOGLE_HANDOFF_KEY,
        GOOGLE_REDIRECT_URI.startswith("https://"),
    ]
):
    raise ImproperlyConfigured("Die Google-Broker-Konfiguration ist unvollständig.")
DEBUG = False
ALLOWED_HOSTS = [name for name in os.environ.get("GOOGLE_BROKER_HOSTS", "").split(",") if name]
if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured("Explizite GOOGLE_BROKER_HOSTS erforderlich.")
DATABASES = {
    "default": dj_database_url.parse(os.environ["GOOGLE_BROKER_DATABASE_URL"], conn_max_age=60)
}
INSTALLED_APPS = ["django.contrib.contenttypes", "google_broker"]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]
ROOT_URLCONF = "google_broker.urls"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LANGUAGE_CODE = "de-de"
TIME_ZONE = "Europe/Berlin"
USE_TZ = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_CONTENT_TYPE_NOSNIFF = True
DATA_UPLOAD_MAX_MEMORY_SIZE = 16384
# Nur aktivieren, wenn der eigene HTTPS-Proxy diesen Header immer selbst setzt.
if os.environ.get("GOOGLE_BROKER_TRUST_PROXY") == "true":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
