"""CalendarContract-Abgleich: keine Netzwerkzugriffe, keine privaten Ereignisinhalte."""

import json
import threading
import uuid
from datetime import UTC, datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from .google_api import parse_instant
from .models import (
    Appointment,
    DeviceBusinessEvent,
    DeviceCalendarConnection,
    DeviceEventBinding,
    DevicePrivateBusy,
)
from .services import audit, snapshot

LOCK = threading.Lock()
REASONS = {
    "missing": "Der zugeordnete Termin ist im Gerätekalender nicht auffindbar. Er könnte gelöscht oder noch nicht wieder synchronisiert sein. Es wird kein Ersatztermin automatisch angelegt.",
    "identity": "Die Zuordnung am Gerät stimmt nicht mehr. Ein fremder Termin wird nicht verändert.",
    "moved": "Der zugeordnete Termin wurde in einen anderen Kalender verschoben. Dort werden keine Inhalte gelesen oder geändert.",
    "duplicate": "Mehrere Geräteereignisse tragen dieselbe Zuordnung. Bitte die Duplikate in der Kalender-App prüfen.",
    "recurring": "Der Geräte-Termin wurde in eine Wiederholungsreihe geändert. Einzelne Vorkommen werden als Belegung berücksichtigt; die Reihe wird hier nicht automatisch verändert.",
    "uncertain": "Die erste Übertragung wurde nicht eindeutig bestätigt. Bitte den Gerätekalender abgleichen. Eine zweite Kopie wird nicht automatisch angelegt.",
    "changed": "Dieser Termin wurde in Haarvinci und im Gerätekalender geändert. Bitte beide Stände vergleichen.",
}


class DeviceError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__("Geräteabgleich nicht abgeschlossen")


class AndroidCalendarBridge:
    def __init__(self):
        from java import jclass

        self.java = jclass("de.haarvinci.app.CalendarProviderBridge")

    def permissions(self):
        return json.loads(str(self.java.permissions()))

    def calendars(self, role):
        return json.loads(str(self.java.calendars(role)))

    def read(self, connection, binding):
        return json.loads(
            str(
                self.java.read(
                    connection.calendar_id,
                    connection.fingerprint,
                    binding.marker.hex,
                    binding.provider_id,
                )
            )
        )

    def write(self, connection, binding, action, revision, payload):
        return json.loads(
            str(
                self.java.write(
                    connection.calendar_id,
                    connection.fingerprint,
                    binding.marker.hex,
                    binding.provider_id,
                    revision,
                    action,
                    json.dumps(payload),
                )
            )
        )

    def instances(self, connection, start, end, skipped):
        return json.loads(
            str(
                self.java.instances(
                    connection.calendar_id,
                    connection.fingerprint,
                    connection.role == "private",
                    int(start.timestamp() * 1000),
                    int(end.timestamp() * 1000),
                    json.dumps(skipped),
                )
            )
        )

    def sync_settings(self, connection):
        return str(self.java.syncSettings(connection.calendar_id, connection.fingerprint))


def permission_info():
    try:
        return AndroidCalendarBridge().permissions()
    except Exception:
        return {"read": False, "write": False}


def local_state(item, binding):
    return {
        "start": item.start_at.astimezone(UTC).isoformat(),
        "end": item.end_at.astimezone(UTC).isoformat(),
        "title": binding.title_override or str(item),
        "notes": item.notes,
        "cancelled": item.status == "cancelled",
    }


def remote_state(response, fallback):
    value = response["event"]
    if value.get("cancelled"):
        return dict(fallback) | {"cancelled": True}
    start, end = parse_instant(value["start"]), parse_instant(value["end"])
    if (
        value.get("all_day")
        or not start < end
        or end - start > timedelta(days=1)
        or len(value.get("notes", "")) > 4000
        or len(value.get("title", "")) > 300
    ):
        raise DeviceError("unsupported")
    return {
        "start": start.astimezone(UTC).isoformat(),
        "end": end.astimezone(UTC).isoformat(),
        "title": value.get("title", ""),
        "notes": value.get("notes", ""),
        "cancelled": False,
    }


@transaction.atomic
def conflict(item, response, state=None, reason="changed"):
    get_user_model().objects.select_for_update().get(pk=item.owner_id)
    current = Appointment.objects.select_for_update().get(pk=item.pk)
    current.sync_state = Appointment.Sync.CONFLICT
    kind = response.get("status", reason)
    current.remote_conflict = dict(state or {}) | {
        "backend": "device",
        "kind": kind,
        "revision": response.get("revision", ""),
        "reason": REASONS.get(reason, REASONS.get(kind, REASONS["changed"])),
        "manageable": kind == "found",
        "missing": kind in ["missing", "uncertain"],
    }
    current.save(update_fields=["sync_state", "remote_conflict"])


@transaction.atomic
def store_result(item, binding, state, response, pull=False):
    get_user_model().objects.select_for_update().get(pk=item.owner_id)
    current = (
        Appointment.objects.select_for_update()
        .select_related("customer", "appointment_type")
        .get(pk=item.pk)
    )
    link = DeviceEventBinding.objects.select_for_update().get(pk=binding.pk)
    if pull and (
        current.version != item.version or local_state(current, link) != local_state(item, binding)
    ):
        conflict(current, response, state)
        return
    if pull:
        before = snapshot(current)
        if state["cancelled"]:
            current.status = Appointment.Status.CANCELLED
        else:
            current.start_at, current.end_at = (
                parse_instant(state["start"]),
                parse_instant(state["end"]),
            )
            current.notes, link.title_override = state["notes"], state["title"]
            if current.status == "cancelled" or (
                current.status == "completed" and current.end_at > timezone.now()
            ):
                current.status = Appointment.Status.CONFIRMED
        current.version += 1
        audit(current, current.owner, before)
    link.baseline, link.revision = state, response.get("revision", "")
    link.last_version = current.version if pull else item.version
    link.provider_id = response.get("id", link.provider_id)
    link.paused = False
    link.save()
    current.sync_state = (
        Appointment.Sync.SYNCED
        if current.version == link.last_version
        else Appointment.Sync.PENDING
    )
    current.remote_conflict = {}
    current.save()


def write_item(item, binding, bridge, state, revision, action):
    result = bridge.write(binding.connection, binding, action, revision, state)
    if result["status"] == "deleted":
        store_result(item, binding, state | {"cancelled": True}, {"id": binding.provider_id})
    elif result["status"] == "found":
        received = remote_state(result, state)
        if received != state:
            conflict(item, result, received)
        else:
            store_result(item, binding, received, result)
    elif result["status"] == "race":
        latest = bridge.read(binding.connection, binding)
        conflict(
            item,
            latest,
            remote_state(latest, binding.baseline or state)
            if latest["status"] == "found"
            else None,
        )
    else:
        if result.get("definite") and action == "insert":
            DeviceEventBinding.objects.filter(pk=binding.pk).update(attempted=False)
        raise DeviceError(result["status"])


def sync_item(item, binding, bridge, writable):
    if binding.paused:
        return None
    response = bridge.read(binding.connection, binding)
    status = response["status"]
    local = local_state(item, binding)
    if (
        status == "missing"
        and not binding.attempted
        and not binding.provider_id
        and not binding.baseline
    ):
        if local["cancelled"]:
            Appointment.objects.filter(pk=item.pk, version=item.version).update(sync_state="local")
            return None
        if not writable:
            raise DeviceError("write")
        # Die Absicht wird vor dem Provider-Aufruf dauerhaft festgehalten.
        DeviceEventBinding.objects.filter(pk=binding.pk).update(attempted=True)
        write_item(item, binding, bridge, local, "", "insert")
        binding.refresh_from_db()
        return binding.provider_id or None
    if status == "missing" and binding.baseline.get("cancelled"):
        if local["cancelled"]:
            Appointment.objects.filter(pk=item.pk, version=item.version).update(
                sync_state="synced", remote_conflict={}
            )
            return None
        # Bewusste lokale Reaktivierung nach einer bestätigten Absage.
        DeviceEventBinding.objects.filter(pk=binding.pk).update(
            marker=uuid.uuid4(), provider_id="", attempted=False, baseline={}, revision=""
        )
        binding.refresh_from_db()
        return sync_item(item, binding, bridge, writable)
    if status != "found":
        if status in ["permission", "calendar", "unavailable"]:
            raise DeviceError(status)
        conflict(
            item,
            response,
            reason="uncertain" if status == "missing" and not binding.provider_id else status,
        )
        return None
    try:
        remote = remote_state(response, binding.baseline or local)
    except DeviceError:
        conflict(item, {"status": "unsupported"}, reason="changed")
        return None
    if item.sync_state == "conflict" and item.remote_conflict.get("backend") == "device":
        conflict(item, response, remote)
        return response["id"]
    local_changed = item.version != binding.last_version or (
        bool(binding.baseline) and local != binding.baseline
    )
    remote_changed = bool(binding.baseline) and remote != binding.baseline
    if (not binding.baseline and remote != local) or (
        local_changed and remote_changed and remote != local
    ):
        conflict(item, response, remote)
    elif remote_changed and not local_changed:
        store_result(item, binding, remote, response, pull=True)
    elif local != remote:
        if not writable:
            raise DeviceError("write")
        if remote["cancelled"] and not local["cancelled"]:
            # Bewusste Reaktivierung einer bereits bestätigten Absage, mit neuer Zuordnung.
            if not binding.baseline.get("cancelled"):
                conflict(item, response, remote)
                return response["id"]
            DeviceEventBinding.objects.filter(pk=binding.pk).update(
                marker=uuid.uuid4(), provider_id="", attempted=False, baseline={}, revision=""
            )
            binding.refresh_from_db()
            sync_item(item, binding, bridge, writable)
        else:
            write_item(
                item,
                binding,
                bridge,
                local,
                response["revision"],
                "delete" if local["cancelled"] else "update",
            )
    elif not response.get("marker_present", True) and writable and not local["cancelled"]:
        write_item(item, binding, bridge, local, response["revision"], "update")
    else:
        store_result(item, binding, remote, response)
    return response["id"]


def active_connections(user=None):
    result = DeviceCalendarConnection.objects.exclude(state="disconnected")
    return result.for_user(user) if user else result


def sync_all(bridge, user=None):
    if not LOCK.acquire(blocking=False):
        return {"message": "Ein Geräteabgleich läuft bereits.", "retry": True}
    retry = False
    try:
        permissions = bridge.permissions()
        for connection in active_connections(user).select_related("owner"):
            if not permissions.get("read"):
                connection.state, connection.error_code = "permission", "read"
                connection.save()
                DevicePrivateBusy.objects.filter(connection=connection).delete()
                DeviceBusinessEvent.objects.filter(connection=connection).delete()
                continue
            try:
                skipped = []
                if connection.role == "business":
                    for item in Appointment.objects.for_user(connection.owner).select_related(
                        "customer", "appointment_type"
                    ):
                        binding, _ = DeviceEventBinding.objects.get_or_create(
                            appointment=item, defaults={"connection": connection}
                        )
                        if binding.connection_id != connection.pk:
                            raise DeviceError("calendar")
                        provider_id = sync_item(
                            item, binding, bridge, permissions.get("write", False)
                        )
                        if provider_id:
                            skipped.append(provider_id)
                day = timezone.localdate()
                start = timezone.make_aware(datetime.combine(day - timedelta(days=90), time()))
                end = timezone.make_aware(datetime.combine(day + timedelta(days=366), time()))
                rows = bridge.instances(connection, start, end, skipped)
                # Alle Antworten validieren, bevor der bisherige Cache ausgetauscht wird.
                intervals = [
                    (row, parse_instant(row["start"]), parse_instant(row["end"])) for row in rows
                ]
                if any(b <= a for _, a, b in intervals):
                    raise DeviceError("unavailable")
                with transaction.atomic():
                    if connection.role == "private":
                        DevicePrivateBusy.objects.filter(connection=connection).delete()
                        DevicePrivateBusy.objects.bulk_create(
                            [
                                DevicePrivateBusy(connection=connection, start_at=a, end_at=b)
                                for a, b in sorted(set((a, b) for _, a, b in intervals))
                            ]
                        )
                    else:
                        DeviceBusinessEvent.objects.filter(connection=connection).delete()
                        unique = {row["id"]: (row, a, b) for row, a, b in intervals}
                        DeviceBusinessEvent.objects.bulk_create(
                            [
                                DeviceBusinessEvent(
                                    connection=connection,
                                    occurrence_key=str(row["id"])[:100],
                                    title=str(row.get("title", "Geschäftlich belegt"))[:300],
                                    start_at=a,
                                    end_at=b,
                                )
                                for row, a, b in unique.values()
                            ]
                        )
                connection.state = "connected"
                connection.error_code = (
                    "conflict"
                    if connection.role == "business"
                    and Appointment.objects.for_user(connection.owner)
                    .filter(sync_state="conflict", remote_conflict__backend="device")
                    .exists()
                    else ""
                )
                connection.last_synced_at, connection.window_start, connection.window_end = (
                    timezone.now(),
                    start,
                    end,
                )
                connection.save()
            except (DeviceError, ValueError, KeyError) as error:
                code = getattr(error, "code", "unavailable")
                connection.state = (
                    "permission" if code in ["permission", "write", "read"] else "error"
                )
                connection.error_code = code
                connection.save(update_fields=["state", "error_code"])
                retry = retry or code == "unavailable"
        return {
            "message": "Geräteabgleich abgeschlossen. Der Google-Abgleich erfolgt separat durch Android.",
            "retry": retry,
            "enabled": active_connections(user).exists(),
        }
    finally:
        LOCK.release()
