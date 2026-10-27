"""Native CalendarContract-Steuerung hinter Anmeldung; keine HTTP-/JavaScript-Brücke."""

import json
import secrets

from django.contrib.auth import get_user_model
from django.db import close_old_connections, transaction

from .device_sync import (
    AndroidCalendarBridge,
    DeviceError,
    active_connections,
    conflict,
    local_state,
    remote_state,
    store_result,
    sync_all,
    write_item,
)
from .models import (
    Appointment,
    DeviceBusinessEvent,
    DeviceCalendarConnection,
    DeviceEventBinding,
    DevicePrivateBusy,
)
from .native import authenticated_user


class DeviceController:
    def __init__(self, bridge):
        self.bridge = bridge

    def choices(self, user, role):
        if role not in ["business", "private"]:
            raise DeviceError("role")
        permissions = self.bridge.permissions()
        if not permissions.get("read") or (role == "business" and not permissions.get("write")):
            raise DeviceError("permission")
        return {"role": role, "calendars": self.bridge.calendars(role)}

    @transaction.atomic
    def choose(self, user, role, selected_id):
        choices = self.choices(user, role)["calendars"]
        selected = next((row for row in choices if row["id"] == selected_id), None)
        if not selected:
            raise DeviceError("calendar")
        get_user_model().objects.select_for_update().get(pk=user.pk)
        if (
            active_connections(user)
            .exclude(role=role)
            .filter(fingerprint=selected["fingerprint"])
            .exists()
        ):
            raise DeviceError("same_calendar")
        connection, _ = DeviceCalendarConnection.objects.get_or_create(
            owner=user,
            role=role,
            defaults={"calendar_id": selected_id, "fingerprint": selected["fingerprint"]},
        )
        if (
            role == "business"
            and DeviceEventBinding.objects.filter(connection=connection).exists()
            and connection.fingerprint != selected["fingerprint"]
        ):
            raise DeviceError("bound_calendar")
        connection.calendar_id, connection.fingerprint = selected_id, selected["fingerprint"]
        connection.state, connection.error_code = "connected", ""
        connection.save()
        return {
            "message": "Gerätekalender ausgewählt. Der Geräteabgleich wird gestartet.",
            "schedule": True,
        }

    @transaction.atomic
    def disconnect(self, user, role):
        if role not in ["business", "private"]:
            raise DeviceError("role")
        connection = DeviceCalendarConnection.objects.for_user(user).filter(role=role).first()
        if connection:
            connection.state, connection.error_code = "disconnected", ""
            connection.save(update_fields=["state", "error_code"])
            DevicePrivateBusy.objects.filter(connection=connection).delete()
            DeviceBusinessEvent.objects.filter(connection=connection).delete()
            if role == "business":
                Appointment.objects.for_user(user).filter(
                    device_binding__connection=connection
                ).update(sync_state="local", remote_conflict={})
        return {"message": "Verbindung getrennt. Termine im Gerätekalender bleiben erhalten."}

    def resolve(self, user, data):
        item = (
            Appointment.objects.for_user(user)
            .select_related("customer", "appointment_type")
            .get(pk=data["appointment"])
        )
        binding = DeviceEventBinding.objects.select_related("connection").get(appointment=item)
        if item.version != int(data["version"]) or not secrets.compare_digest(
            item.conflict_token, data.get("proof", "")
        ):
            raise DeviceError("stale")
        response = self.bridge.read(binding.connection, binding)
        status = response["status"]
        if data["choice"] == "check":
            if status == "found":
                conflict(
                    item,
                    response,
                    remote_state(response, binding.baseline or local_state(item, binding)),
                )
                return {
                    "message": "Zuordnung wiedergefunden. Bitte die beiden Stände erneut prüfen."
                }
            return {
                "message": "Die Zuordnung ist weiterhin unklar. Es wurde kein Geräte-Termin angelegt oder verändert."
            }
        shown = item.remote_conflict
        if status != shown.get("kind") or (
            status == "found" and response.get("revision") != shown.get("revision")
        ):
            conflict(
                item,
                response,
                remote_state(response, binding.baseline or local_state(item, binding))
                if status == "found"
                else None,
            )
            raise DeviceError("stale")
        if status == "found":
            remote = remote_state(response, binding.baseline or local_state(item, binding))
            if data["choice"] == "remote":
                store_result(item, binding, remote, response, pull=True)
            elif data["choice"] == "local":
                if remote["cancelled"] and item.status != "cancelled":
                    raise DeviceError("missing")
                write_item(
                    item,
                    binding,
                    self.bridge,
                    local_state(item, binding),
                    response["revision"],
                    "delete" if item.status == "cancelled" else "update",
                )
            else:
                raise DeviceError("choice")
        elif status == "missing":
            if data["choice"] == "remote":
                store_result(
                    item,
                    binding,
                    (binding.baseline or local_state(item, binding)) | {"cancelled": True},
                    {},
                    pull=True,
                )
            elif data["choice"] == "local":
                with transaction.atomic():
                    get_user_model().objects.select_for_update().get(pk=user.pk)
                    current = Appointment.objects.select_for_update().get(pk=item.pk)
                    if current.version != item.version:
                        raise DeviceError("stale")
                    DeviceEventBinding.objects.filter(pk=binding.pk).update(paused=True)
                    current.sync_state = "local"
                    current.save(update_fields=["sync_state"])
            else:
                raise DeviceError("choice")
        else:
            raise DeviceError("identity")
        return {"message": "Entscheidung verarbeitet. Bitte den Termin prüfen."}


MESSAGES = {
    "permission": "Bitte die benötigte Kalenderberechtigung erteilen. Der lokale Haarvinci-Kalender bleibt nutzbar.",
    "same_calendar": "Geschäftlicher und privater Kalender müssen verschieden sein.",
    "bound_calendar": "Bereits zugeordnete Termine gehören zu einem anderen Gerätekalender. Bitte denselben Kalender wieder auswählen.",
    "calendar": "Der ausgewählte Kalender ist nicht mehr eindeutig verfügbar. Bitte die Auswahl prüfen.",
    "stale": "Der Termin wurde inzwischen geändert. Bitte die Vorschau erneut öffnen und prüfen.",
    "identity": "Die Zuordnung ist unklar. Der Geräte-Termin wurde nicht verändert.",
    "missing": "Ein fehlender Termin wird nicht automatisch erneut angelegt. Bitte die Kalender-App und die Android-Kontosynchronisierung prüfen.",
}


def action(cookies, action_name, arguments):
    close_old_connections()
    try:
        user = authenticated_user(cookies)
        controller = DeviceController(AndroidCalendarBridge())
        data = json.loads(arguments or "{}")
        if action_name == "select":
            result = controller.choices(user, data.get("role"))
        elif action_name == "choose":
            result = controller.choose(user, data.get("role"), data.get("calendar_id"))
        elif action_name == "sync":
            result = sync_all(controller.bridge, user)
        elif action_name == "disconnect":
            result = controller.disconnect(user, data.get("role"))
        elif action_name == "resolve":
            result = controller.resolve(user, data)
        else:
            raise DeviceError("action")
        return json.dumps(result)
    except Exception as error:
        return json.dumps(
            {
                "message": MESSAGES.get(
                    getattr(error, "code", ""),
                    "Der Geräteabgleich konnte nicht abgeschlossen werden. Bitte Berechtigungen und Kalenderauswahl prüfen.",
                )
            }
        )
    finally:
        close_old_connections()


def background():
    close_old_connections()
    try:
        return json.dumps(sync_all(AndroidCalendarBridge()))
    finally:
        close_old_connections()
