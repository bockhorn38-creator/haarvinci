from datetime import UTC, timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from customers.models import CustomerEvent
from customers.services import EditConflict

from .models import Appointment, CalendarConnection, PrivateBusy, RemoteBusinessEvent

EDITABLE = [
    "customer",
    "appointment_type",
    "start_at",
    "end_at",
    "buffer_minutes",
    "notes",
    "status",
]


class ScheduleConflict(Exception):
    def __init__(self, entries):
        self.entries = entries


def conflicts(*, user, start, end, buffer=0, exclude=None):
    until = end.astimezone(UTC) + timedelta(minutes=buffer)
    result = []
    others = (
        Appointment.objects.for_user(user)
        .exclude(status=Appointment.Status.CANCELLED)
        .filter(start_at__lt=until, end_at__gt=start - timedelta(minutes=240))
        .select_related("customer", "appointment_type")
    )
    if exclude:
        others = others.exclude(pk=exclude)
    for other in others:
        if other.busy_until > start:
            result.append({"label": str(other), "start": other.start_at, "end": other.busy_until})
    for model, label in [
        (PrivateBusy, "Privat belegt"),
        (RemoteBusinessEvent, "Google geschäftlich belegt"),
    ]:
        for block in model.objects.filter(
            connection__owner=user, start_at__lt=until, end_at__gt=start
        ):
            result.append({"label": label, "start": block.start_at, "end": block.end_at})
    return result


def snapshot(appointment):
    return {
        "customer": str(appointment.customer),
        "appointment_type": str(appointment.appointment_type),
        "start_at": timezone.localtime(appointment.start_at).isoformat(),
        "end_at": timezone.localtime(appointment.end_at).isoformat(),
        "buffer_minutes": str(appointment.buffer_minutes),
        "notes": appointment.notes,
        "status": appointment.get_status_display(),
    }


def audit(appointment, user, before=None):
    after = snapshot(appointment)
    labels = {
        "customer": "Kundin",
        "appointment_type": "Terminart",
        "start_at": "Beginn",
        "end_at": "Ende",
        "buffer_minutes": "Puffer (Minuten)",
        "notes": "Terminnotizen",
        "status": "Terminstatus",
    }
    changes = [
        {"field": key, "label": labels[key], "before": before[key], "after": after[key]}
        for key in after
        if before and before[key] != after[key]
    ]
    kind = (
        "appointment_created"
        if before is None
        else (
            "appointment_cancelled"
            if appointment.status == Appointment.Status.CANCELLED
            else "appointment_updated"
        )
    )
    if before is None or changes:
        CustomerEvent.objects.create(
            customer=appointment.customer,
            actor=user,
            kind=kind,
            occurred_on=timezone.localdate(),
            appointment_uuid=appointment.pk,
            summary=f"{appointment.appointment_type} · {timezone.localtime(appointment.start_at).strftime('%d.%m.%Y, %H:%M')}",
            snapshot=after,
            changes=changes,
        )


@transaction.atomic
def save_appointment(*, user, data, appointment_id=None):
    get_user_model().objects.select_for_update().get(pk=user.pk)
    if appointment_id:
        item = (
            Appointment.objects.for_user(user)
            .select_for_update()
            .select_related("customer", "appointment_type")
            .get(pk=appointment_id)
        )
        if item.version != data.get("version"):
            raise EditConflict
        before = snapshot(item)
    else:
        item = Appointment(owner=user)
        before = None
    # Dienste prüfen die Zuordnung zusätzlich zu den eigentümerbegrenzten Formularen.
    if data["customer"].owner_id != user.pk or data["appointment_type"].owner_id not in [
        None,
        user.pk,
    ]:
        raise ValueError("Ungültige Zuordnung")
    found = (
        []
        if data["status"] == Appointment.Status.CANCELLED
        else conflicts(
            user=user,
            start=data["start_at"],
            end=data["end_at"],
            buffer=data["buffer_minutes"],
            exclude=appointment_id,
        )
    )
    if found and not data.get("allow_overlap"):
        raise ScheduleConflict(found)
    old_customer = item.customer if appointment_id else None
    for field in EDITABLE:
        setattr(item, field, data[field])
    if appointment_id:
        item.version += 1
    item.sync_state = (
        Appointment.Sync.PENDING
        if item.google_event_id
        or CalendarConnection.objects.filter(owner=user, role="business")
        .exclude(calendar_id="")
        .exists()
        else Appointment.Sync.LOCAL
    )
    item.save()
    if old_customer and old_customer != item.customer:
        CustomerEvent.objects.create(
            customer=old_customer,
            actor=user,
            kind="appointment_updated",
            occurred_on=timezone.localdate(),
            appointment_uuid=item.pk,
            summary="Termin einer anderen Kundenakte zugeordnet",
            snapshot=before,
        )
    audit(item, user, before if old_customer == item.customer else None)
    return item


@transaction.atomic
def cancel_appointment(*, user, appointment_id, version):
    get_user_model().objects.select_for_update().get(pk=user.pk)
    item = (
        Appointment.objects.for_user(user)
        .select_for_update()
        .select_related("customer", "appointment_type")
        .get(pk=appointment_id)
    )
    if item.version != version:
        raise EditConflict
    if item.status != Appointment.Status.CANCELLED:
        before = snapshot(item)
        item.status = Appointment.Status.CANCELLED
        item.version += 1
        item.sync_state = Appointment.Sync.PENDING if item.google_event_id else item.sync_state
        item.save()
        audit(item, user, before)
    return item
