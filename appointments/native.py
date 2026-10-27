"""Privater Android-Einstieg, ohne Token-Endpunkte oder JavaScript-Brücke im WebView."""

import base64
import hashlib
import json
import secrets
import time
from http.cookies import SimpleCookie

from django.conf import settings
from django.contrib.auth import get_user
from django.contrib.sessions.backends.db import SessionStore
from django.db import close_old_connections
from django.http import HttpRequest

from .forms import validate_broker_url
from .google_api import GoogleCalendarAPI, GoogleError, request_json
from .models import Appointment, CalendarConnection, CalendarSettings
from .sync import _SYNC_LOCK, resolve_conflict, sync_connection


def authenticated_user(cookie_header):
    jar = SimpleCookie()
    jar.load(cookie_header or "")
    gate = jar.get("haarvinci_android_gate")
    if not gate or not secrets.compare_digest(gate.value, settings.DESKTOP_TOKEN):
        raise GoogleError(403)
    session = jar.get(settings.SESSION_COOKIE_NAME)
    request = HttpRequest()
    request.session = SessionStore(session_key=session.value if session else None)
    user = get_user(request)
    if not user.is_authenticated:
        raise GoogleError(403)
    return user


class AndroidVault:
    def __init__(self, context):
        from java import jclass

        self.context, self.store = context, jclass("de.haarvinci.app.GoogleVault")

    def load(self, key):
        raw = str(self.store.load(self.context, key))
        return json.loads(raw) if raw else {}

    def save(self, key, value):
        if value:
            self.store.save(self.context, key, json.dumps(value))
        else:
            self.store.remove(self.context, key)


def vault_key(connection):
    return f"google:{connection.owner_id}:{connection.pk}"


class GoogleController:
    def __init__(self, vault, api_factory=GoogleCalendarAPI, http=request_json):
        self.vault, self.api_factory, self.http = vault, api_factory, http

    def broker(self, record, path, data):
        base = validate_broker_url(record["broker"])
        return self.http(base + path, method="POST", data=data)

    def begin(self, user, role):
        if role not in CalendarConnection.Role.values:
            raise GoogleError(400)
        config, _ = CalendarSettings.objects.get_or_create(owner=user)
        if not config.broker_url:
            return {"message": "Bitte zuerst den eigenen HTTPS-Anmeldedienst einrichten."}
        connection, _ = CalendarConnection.objects.get_or_create(owner=user, role=role)
        key = vault_key(connection)
        if self.vault.load(key).get("token") and connection.state != CalendarConnection.State.AUTH:
            return {
                "message": "Diese Verbindung besteht bereits. Zum Kontowechsel bitte zuerst trennen."
            }
        # Auf Android ist der Broker nicht installiert: derselbe standardisierte S256-Ausdruck lokal.
        verifier, device_key = secrets.token_urlsafe(64), secrets.token_urlsafe(48)
        record = {
            "broker": config.broker_url,
            "verifier": verifier,
            "device_key": device_key,
            "pending_since": time.time(),
        }
        result = self.broker(
            record,
            "/mobil/start/",
            {
                "role": role,
                "challenge": base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
                .decode()
                .rstrip("="),
                "device_key": device_key,
            },
        )
        record["handoff_id"] = result["id"]
        self.vault.save(key, record)
        connection.state, connection.error_code = CalendarConnection.State.PENDING, ""
        connection.save()
        return {
            "browser_url": result["authorization_url"],
            "message": "Nach der Google-Anmeldung zurück zur Haarvinci-App wechseln.",
        }

    def finish(self, user):
        for connection in CalendarConnection.objects.for_user(user):
            key = vault_key(connection)
            record = self.vault.load(key)
            if record.get("handoff_id"):
                if time.time() - record["pending_since"] > 600:
                    self.vault.save(key, {})
                    connection.state = CalendarConnection.State.AUTH
                    connection.save(update_fields=["state"])
                    continue
                try:
                    result = self.broker(
                        record,
                        "/mobil/abschliessen/",
                        {"id": record["handoff_id"], "verifier": record["verifier"]},
                    )
                except GoogleError as error:
                    if error.code == 400:
                        self.vault.save(key, {})
                        connection.state = CalendarConnection.State.AUTH
                        connection.save(update_fields=["state"])
                    raise
                if result.get("status") == "pending":
                    continue
                record["token"], record["device_id"] = result["token"], result["device_id"]
                record.pop("verifier", None)
                record.pop("handoff_id", None)
                self.vault.save(key, record)
                connection.state = CalendarConnection.State.CHOOSE
                connection.save(update_fields=["state"])
            if connection.state == CalendarConnection.State.CHOOSE and record.get("token"):
                return self.calendar_choices(connection)
        return {"message": "Verbindungsstand geprüft."}

    def api(self, connection):
        key = vault_key(connection)
        try:
            record = self.vault.load(key)
        except Exception as error:
            raise GoogleError(401) from error
        config = CalendarSettings.objects.get(owner=connection.owner)
        if not record.get("token") or record.get("broker") != config.broker_url:
            raise GoogleError(401)
        token = record["token"]
        expiry = token.get("expires_at", 0)
        if not expiry:
            expiry = time.time() + float(token.get("expires_in", 3600))
            token["expires_at"] = expiry
            self.vault.save(key, record)
        if expiry < time.time() + 120:
            result = self.broker(
                record,
                "/mobil/erneuern/",
                {
                    "device_id": record["device_id"],
                    "device_key": record["device_key"],
                    "refresh_token": token["refresh_token"],
                },
            )
            refreshed = result["token"]
            refreshed.setdefault("refresh_token", token["refresh_token"])
            record["token"] = token = refreshed
            self.vault.save(key, record)
        return self.api_factory(token["access_token"], connection.role)

    def calendar_choices(self, connection):
        api = self.api(connection)
        return {
            "role": connection.role,
            "calendars": [
                {"id": item["id"], "title": item.get("summary", "Google-Kalender")}
                for item in api.calendars()
            ],
        }

    def choose(self, user, role, calendar_id):
        connection = CalendarConnection.objects.for_user(user).get(role=role)
        valid = {item["id"] for item in self.api(connection).calendars()}
        if calendar_id not in valid:
            raise GoogleError(403)
        if (
            role == "business"
            and Appointment.objects.for_user(user)
            .exclude(google_calendar_id="")
            .exclude(google_calendar_id=calendar_id)
            .exists()
        ):
            return {
                "message": "Vorhandene Haarvinci-Termine sind einem anderen Google-Kalender zugeordnet. Bitte wähle für diesen Testbestand denselben Kalender."
            }
        connection.calendar_id, connection.state = calendar_id, CalendarConnection.State.CONNECTED
        connection.save()
        self.sync(user)
        return {
            "message": "Der Kalender wurde verbunden. Der Synchronisierungsstand steht in den Einstellungen."
        }

    def disconnect(self, user, role):
        connection = CalendarConnection.objects.for_user(user).filter(role=role).first()
        if connection:
            key = vault_key(connection)
            record = self.vault.load(key)
            try:
                if record.get("device_id"):
                    self.broker(
                        record,
                        "/mobil/trennen/",
                        {"device_id": record["device_id"], "device_key": record["device_key"]},
                    )
            except GoogleError:
                pass  # Lokales Trennen muss auch offline möglich sein.
            self.vault.save(key, {})
            connection.delete()  # Entfernt nur lokale Belegungs-Caches, keine Google-Termine.
        return {
            "message": "Verbindung auf diesem Gerät getrennt. Google-Termine bleiben unverändert."
        }

    def sync(self, user=None):
        if not _SYNC_LOCK.acquire(blocking=False):
            return {"message": "Eine Synchronisierung läuft bereits."}
        try:
            connections = CalendarConnection.objects.exclude(calendar_id="").exclude(
                state__in=["disconnected", "pending", "choose", "auth"]
            )
            if user:
                connections = connections.for_user(user)
            failures = 0
            retry = False
            for connection in connections.select_related("owner"):
                try:
                    sync_connection(connection, self.api(connection))
                except (GoogleError, ValueError, KeyError) as error:
                    failures += 1
                    code = getattr(error, "code", 422)
                    retry = retry or code == 0 or code == 429 or code >= 500
                    connection.state = (
                        CalendarConnection.State.AUTH
                        if code == 401
                        else CalendarConnection.State.ERROR
                    )
                    connection.error_code = {
                        0: "offline",
                        401: "auth",
                        403: "permission",
                        409: "calendar_changed",
                        429: "limit",
                    }.get(code, "request")
                    connection.save(update_fields=["state", "error_code"])
            return {
                "message": "Synchronisierung geprüft."
                if not failures
                else "Synchronisierung noch nicht abgeschlossen. Details stehen bei den Google-Verbindungen.",
                "retry": retry,
            }
        finally:
            _SYNC_LOCK.release()

    def resolve(self, user, item_id, version, choice):
        connection = CalendarConnection.objects.for_user(user).get(role="business")
        resolve_conflict(
            user=user,
            appointment_id=item_id,
            version=version,
            choice=choice,
            api=self.api(connection),
            connection=connection,
        )
        return {"message": "Konfliktentscheidung verarbeitet. Bitte prüfe den Termin erneut."}


def action(cookie_header, action_name, arguments, context):
    close_old_connections()
    try:
        user = authenticated_user(cookie_header)
        controller = GoogleController(AndroidVault(context))
        data = json.loads(arguments or "{}")
        if action_name == "connect":
            result = controller.begin(user, data.get("role"))
        elif action_name == "finish":
            result = controller.finish(user)
        elif action_name == "choose":
            result = controller.choose(user, data.get("role"), data.get("calendar_id"))
        elif action_name == "disconnect":
            result = controller.disconnect(user, data.get("role"))
        elif action_name == "sync":
            result = controller.sync(user)
        elif action_name == "resolve":
            result = controller.resolve(
                user, data["appointment"], int(data["version"]), data["choice"]
            )
        elif action_name == "calendars":
            result = controller.calendar_choices(
                CalendarConnection.objects.for_user(user).get(role=data["role"])
            )
        else:
            raise GoogleError(400)
        return json.dumps(result)
    except Exception:
        return json.dumps(
            {
                "message": "Die Google-Aktion konnte noch nicht abgeschlossen werden. Bitte prüfe Einrichtung, Verbindung und Anmeldung."
            }
        )
    finally:
        close_old_connections()


def background(context):
    close_old_connections()
    try:
        return json.dumps(GoogleController(AndroidVault(context)).sync())
    finally:
        close_old_connections()
