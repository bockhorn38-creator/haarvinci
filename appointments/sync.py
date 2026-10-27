"""Offline-Outbox mit deterministischen IDs, ETags und expliziter Konfliktauflösung."""

import threading
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from .google_api import GoogleError, parse_instant
from .models import (
    Appointment,
    CalendarConnection,
    CalendarSettings,
    PrivateBusy,
    RemoteBusinessEvent,
)
from .services import audit

_SYNC_LOCK = threading.Lock()


def parse_boundary(value, zone="Europe/Berlin"):
    if "dateTime" in value:
        return parse_instant(value["dateTime"])
    try:
        return datetime.combine(
            datetime.strptime(value["date"], "%Y-%m-%d").date(), time(), ZoneInfo(zone)
        )
    except (ValueError, KeyError):
        raise GoogleError(422) from None


def event_id(item):
    return (
        "h" + item.pk.hex + (format(item.google_generation, "x") if item.google_generation else "")
    )


def owned(remote, item, settings):
    props = remote.get("extendedProperties", {}).get("private", {})
    return (
        remote.get("id") == event_id(item)
        and props.get("haarvinciInstall") == settings.instance_id.hex
        and props.get("haarvinciId") == item.pk.hex
    )


def canonical(remote, fallback=None):
    if remote.get("status") == "cancelled":
        return dict(fallback or {}) | {"cancelled": True}
    start, end = parse_boundary(remote["start"]), parse_boundary(remote["end"])
    if end <= start or end - start > timedelta(hours=24):
        raise GoogleError(422)
    title, notes = remote.get("summary", ""), remote.get("description", "")
    if len(title) > 300 or len(notes) > 4000:
        raise GoogleError(422)
    return {
        "start": start.astimezone(UTC).isoformat(),
        "end": end.astimezone(UTC).isoformat(),
        "title": title,
        "notes": notes,
        "cancelled": False,
    }


def local_state(item):
    return {
        "start": item.start_at.astimezone(UTC).isoformat(),
        "end": item.end_at.astimezone(UTC).isoformat(),
        "title": item.google_title or str(item),
        "notes": item.notes,
        "cancelled": item.status == "cancelled",
    }


def payload(item, settings):
    state = local_state(item)
    return {
        "id": event_id(item),
        "summary": state["title"],
        "description": state["notes"],
        "start": {"dateTime": state["start"], "timeZone": "Europe/Berlin"},
        "end": {"dateTime": state["end"], "timeZone": "Europe/Berlin"},
        "extendedProperties": {
            "private": {"haarvinciInstall": settings.instance_id.hex, "haarvinciId": item.pk.hex}
        },
    }


@transaction.atomic
def flag_conflict(item, state, etag="", manageable=True):
    get_user_model().objects.select_for_update().get(pk=item.owner_id)
    current = Appointment.objects.select_for_update().get(pk=item.pk)
    current.sync_state = Appointment.Sync.CONFLICT
    current.remote_conflict = state | {"etag": etag, "manageable": manageable}
    current.save(update_fields=["sync_state", "remote_conflict"])


@transaction.atomic
def accept_remote(item, state, etag, calendar_id):
    get_user_model().objects.select_for_update().get(pk=item.owner_id)
    current = (
        Appointment.objects.select_for_update()
        .select_related("customer", "appointment_type")
        .get(pk=item.pk)
    )
    if current.version != item.version:
        flag_conflict(current, state, etag)
        return False
    before_status = current.status
    from .services import snapshot

    before = snapshot(current)
    if state.get("cancelled"):
        current.status = Appointment.Status.CANCELLED
    else:
        current.start_at, current.end_at = (
            parse_instant(state["start"]),
            parse_instant(state["end"]),
        )
        current.notes, current.google_title = state["notes"], state["title"]
        if before_status == Appointment.Status.CANCELLED or (
            before_status == Appointment.Status.COMPLETED and current.end_at > timezone.now()
        ):
            current.status = Appointment.Status.CONFIRMED
    current.version += 1
    current.google_event_id = event_id(item)
    current.google_calendar_id = calendar_id
    current.google_etag, current.google_baseline = etag, state
    current.last_synced_version = current.version
    current.sync_state, current.remote_conflict = Appointment.Sync.SYNCED, {}
    current.save()
    audit(current, current.owner, before)
    return True


@transaction.atomic
def mark_sent(item, remote_state, etag, calendar_id):
    get_user_model().objects.select_for_update().get(pk=item.owner_id)
    current = Appointment.objects.select_for_update().get(pk=item.pk)
    current.google_event_id = event_id(item)
    current.google_calendar_id = calendar_id
    current.google_etag, current.google_baseline = etag, remote_state
    current.last_synced_version = item.version
    current.sync_state = (
        Appointment.Sync.SYNCED if current.version == item.version else Appointment.Sync.PENDING
    )
    current.remote_conflict = {}
    current.save(
        update_fields=[
            "google_event_id",
            "google_calendar_id",
            "google_etag",
            "google_baseline",
            "last_synced_version",
            "sync_state",
            "remote_conflict",
        ]
    )


def sync_item(item, connection, settings, api):
    if item.google_calendar_id and item.google_calendar_id != connection.calendar_id:
        raise GoogleError(409)
    remote_id = event_id(item)
    try:
        remote = api.event(connection.calendar_id, remote_id)
    except GoogleError as error:
        if error.code not in [404, 410]:
            raise
        remote = {"id": remote_id, "status": "cancelled"} if item.google_event_id else None
    if (
        remote is not None
        and remote.get("status") != "cancelled"
        and not owned(remote, item, settings)
    ):
        flag_conflict(
            item,
            {"reason": "Die Google-Identität passt nicht zu diesem Haarvinci-Termin."},
            manageable=False,
        )
        return
    if remote is None:
        if item.status == "cancelled":
            return
        try:
            result = api.insert(connection.calendar_id, payload(item, settings))
        except GoogleError as error:
            if error.code == 409:
                # Unklarer Insert-Ausgang wird über die feste ID im nächsten Lauf abgeglichen.
                Appointment.objects.filter(pk=item.pk).update(sync_state=Appointment.Sync.PENDING)
            raise
        mark_sent(item, canonical(result), result.get("etag", ""), connection.calendar_id)
        return
    if remote.get("status") != "cancelled" and not remote.get("etag"):
        raise GoogleError(422)
    state = canonical(remote, item.google_baseline or local_state(item))
    etag = remote.get("etag", item.google_etag)
    if not item.google_baseline and state != local_state(item):
        # Ein früherer Insert kann erfolgreich gewesen sein, obwohl seine Antwort verloren ging.
        # Ohne Vergleichsstand werden abweichende Google-Daten niemals still überschrieben.
        flag_conflict(item, state, etag)
        return
    remote_changed = bool(item.google_baseline) and state != item.google_baseline
    local_changed = item.version != item.last_synced_version
    if item.sync_state == Appointment.Sync.CONFLICT or (
        remote_changed and local_changed and state != local_state(item)
    ):
        flag_conflict(item, state, etag)
        return
    if remote_changed and not local_changed:
        accept_remote(item, state, etag, connection.calendar_id)
        return
    if local_changed and state != local_state(item):
        try:
            if item.status == "cancelled":
                if not state.get("cancelled"):
                    api.event(connection.calendar_id, remote_id, method="DELETE", etag=etag)
                mark_sent(item, state | {"cancelled": True}, etag, connection.calendar_id)
            else:
                if state.get("cancelled"):
                    # Gelöschte Google-Termine werden ohne explizite Konfliktentscheidung nicht neu angelegt.
                    flag_conflict(item, state, etag)
                    return
                body = payload(item, settings)
                body.pop("id")
                result = api.event(
                    connection.calendar_id, remote_id, method="PATCH", data=body, etag=etag
                )
                mark_sent(item, canonical(result), result.get("etag", ""), connection.calendar_id)
        except GoogleError as error:
            if error.code == 412:
                latest = api.event(connection.calendar_id, remote_id)
                flag_conflict(item, canonical(latest, state), latest.get("etag", ""))
                return
            raise
    else:
        mark_sent(item, state, etag, connection.calendar_id)


def window():
    now = timezone.now()
    return now - timedelta(days=90), now + timedelta(days=365)


def sync_connection(connection, api):
    if not connection.calendar_id:
        return
    start, end = window()
    if connection.role == "private":
        response = api.busy(connection.calendar_id, start, end)
        calendar = response.get("calendars", {}).get(connection.calendar_id)
        if not calendar or calendar.get("errors"):
            raise GoogleError(403)
        # Nur diese beiden Werte verlassen die FreeBusy-Antwort. Keine privaten Metadaten persistieren.
        intervals = sorted(
            set(
                (parse_instant(item["start"]), parse_instant(item["end"]))
                for item in calendar.get("busy", [])
            )
        )
        if any(b <= a for a, b in intervals):
            raise GoogleError(422)
        with transaction.atomic():
            PrivateBusy.objects.filter(connection=connection).delete()
            PrivateBusy.objects.bulk_create(
                [PrivateBusy(connection=connection, start_at=a, end_at=b) for a, b in intervals]
            )
    else:
        settings, _ = CalendarSettings.objects.get_or_create(owner=connection.owner)
        remote_items, zone = api.events(connection.calendar_id, start, end)
        local = list(
            Appointment.objects.for_user(connection.owner).select_related(
                "customer", "appointment_type"
            )
        )
        known = {event_id(item): item for item in local}
        foreign = []
        for event in remote_items:
            if event.get("status") == "cancelled" or event.get("transparency") == "transparent":
                continue
            if event.get("id") in known and owned(event, known[event["id"]], settings):
                continue
            a, b = parse_boundary(event["start"], zone), parse_boundary(event["end"], zone)
            if b <= a:
                raise GoogleError(422)
            foreign.append(
                RemoteBusinessEvent(
                    connection=connection,
                    remote_id=event["id"],
                    title=str(event.get("summary", "Google-Termin"))[:300],
                    start_at=a,
                    end_at=b,
                )
            )
        # Erst nach vollständigem, paginiertem Abruf den bisherigen Cache austauschen.
        with transaction.atomic():
            RemoteBusinessEvent.objects.filter(connection=connection).delete()
            RemoteBusinessEvent.objects.bulk_create(foreign)
        for item in local:
            sync_item(item, connection, settings, api)
    conflict = (
        connection.role == "business"
        and Appointment.objects.for_user(connection.owner).filter(sync_state="conflict").exists()
    )
    connection.state = (
        CalendarConnection.State.ERROR if conflict else CalendarConnection.State.CONNECTED
    )
    connection.error_code = "conflict" if conflict else ""
    connection.last_synced_at, connection.window_start, connection.window_end = (
        timezone.now(),
        start,
        end,
    )
    connection.save()


def resolve_conflict(*, user, appointment_id, version, choice, api, connection):
    item = (
        Appointment.objects.for_user(user)
        .select_related("customer", "appointment_type")
        .get(pk=appointment_id)
    )
    settings = CalendarSettings.objects.get(owner=user)
    if item.version != version or not item.remote_conflict.get("manageable"):
        raise GoogleError(409)
    try:
        remote = api.event(connection.calendar_id, event_id(item))
    except GoogleError as error:
        if error.code not in [404, 410]:
            raise
        remote = {"status": "cancelled", "etag": item.remote_conflict.get("etag", "")}
    if remote.get("status") != "cancelled" and not owned(remote, item, settings):
        raise GoogleError(409)
    state = canonical(remote, item.google_baseline)
    if remote.get("etag", "") != item.remote_conflict.get("etag", ""):
        flag_conflict(item, state, remote.get("etag", ""))
        raise GoogleError(409)
    if choice == "remote":
        accept_remote(item, state, remote.get("etag", ""), connection.calendar_id)
    elif choice == "local":
        with transaction.atomic():
            get_user_model().objects.select_for_update().get(pk=user.pk)
            current = Appointment.objects.select_for_update().get(pk=item.pk)
            if current.version != version:
                raise GoogleError(409)
            if state.get("cancelled") and item.status != "cancelled":
                current.google_generation += 1
                current.google_event_id = ""
                current.google_baseline, current.google_etag = {}, ""
            else:
                current.google_baseline, current.google_etag = state, remote.get("etag", "")
            current.sync_state, current.remote_conflict = Appointment.Sync.PENDING, {}
            current.last_synced_version = 0
            current.save(
                update_fields=[
                    "google_generation",
                    "google_event_id",
                    "google_baseline",
                    "google_etag",
                    "sync_state",
                    "remote_conflict",
                    "last_synced_version",
                ]
            )
        sync_item(current, connection, settings, api)
    else:
        raise GoogleError(400)
