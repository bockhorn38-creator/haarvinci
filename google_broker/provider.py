"""Nur auf dem optionalen HTTPS-Dienst; offizielle Google-OAuth-Bibliothek."""

import json
from datetime import UTC
from functools import partial

from django.conf import settings


def flow(role, verifier, state=None):
    from google_auth_oauthlib.flow import Flow

    from appointments.google_api import SCOPES

    return Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
            }
        },
        scopes=SCOPES[role],
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
        state=state,
        code_verifier=verifier,
        autogenerate_code_verifier=False,
    )


def authorization_url(role, verifier, state):
    return flow(role, verifier, state).authorization_url(
        access_type="offline", prompt="consent select_account", include_granted_scopes="false"
    )[0]


def exchange(role, verifier, code):
    google = flow(role, verifier)
    google.fetch_token(code=code, timeout=20)
    return dict(google.oauth2session.token)


def refresh(role, refresh_token):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    from appointments.google_api import SCOPES

    credentials = Credentials(
        None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=SCOPES[role],
    )
    credentials.refresh(partial(Request(), timeout=20))
    return {
        "access_token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "expires_at": credentials.expiry.replace(tzinfo=UTC).timestamp(),
    }


def encrypt(payload):
    from cryptography.fernet import Fernet

    return (
        Fernet(settings.GOOGLE_HANDOFF_KEY.encode()).encrypt(json.dumps(payload).encode()).decode()
    )


def decrypt(payload):
    from cryptography.fernet import Fernet

    return json.loads(Fernet(settings.GOOGLE_HANDOFF_KEY.encode()).decrypt(payload.encode()))
