from config.desktop_settings import *  # noqa: F403
from config.desktop_settings import MIDDLEWARE

ANDROID_MODE = True
MIDDLEWARE = ["android_backend.middleware.AndroidGateMiddleware", *MIDDLEWARE[1:]]
SESSION_COOKIE_NAME = "haarvinci_android_session"
