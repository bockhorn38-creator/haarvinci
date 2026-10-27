"""ORM-Regressionstests auf dem Desktop-Speicher; Zugriffssperre separat testen."""

from config.desktop_settings import *  # noqa: F403
from config.desktop_settings import INSTALLED_APPS, MIDDLEWARE

INSTALLED_APPS = [*INSTALLED_APPS, "google_broker"]

MIDDLEWARE = [
    entry for entry in MIDDLEWARE if entry != "desktop_app.middleware.DesktopGateMiddleware"
]
