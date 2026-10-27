import calendar
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.urls import reverse
from django.utils import timezone

from .models import Appointment, CalendarConnection, PrivateBusy, RemoteBusinessEvent

BERLIN = ZoneInfo("Europe/Berlin")


def midnight(day):
    return datetime.combine(day, time(), BERLIN)


def entries_for_range(user, first, last, customer=None):
    start, end = midnight(first), midnight(last + timedelta(days=1))
    items = (
        Appointment.objects.for_user(user)
        .filter(start_at__lt=end, end_at__gt=start - timedelta(minutes=240))
        .select_related("customer", "appointment_type")
    )
    if customer:
        items = items.filter(customer=customer)
    result = [
        {
            "id": str(item.pk),
            "title": str(item.customer),
            "subtitle": str(item.appointment_type),
            "start": item.start_at,
            "end": item.end_at,
            "busy_end": item.end_at,
            "kind": "appointment",
            "cancelled": item.status == "cancelled",
            "status": item.get_status_display(),
            "url": reverse("appointments:detail", args=[item.pk]),
        }
        for item in items
    ]
    for item in items:
        if item.buffer_minutes and item.status != "cancelled":
            result.append(
                {
                    "title": "Puffer nach Termin",
                    "subtitle": str(item.customer),
                    "start": item.end_at,
                    "end": item.busy_until,
                    "busy_end": item.busy_until,
                    "kind": "buffer",
                    "cancelled": False,
                    "url": reverse("appointments:detail", args=[item.pk]),
                }
            )
    if not customer:
        for block in PrivateBusy.objects.filter(
            connection__owner=user, start_at__lt=end, end_at__gt=start
        ):
            result.append(
                {
                    "title": "Privat belegt",
                    "subtitle": "Privater Google-Kalender",
                    "start": block.start_at,
                    "end": block.end_at,
                    "busy_end": block.end_at,
                    "kind": "private",
                    "cancelled": False,
                }
            )
        for block in RemoteBusinessEvent.objects.filter(
            connection__owner=user, start_at__lt=end, end_at__gt=start
        ):
            result.append(
                {
                    "title": block.title or "Google-Termin",
                    "subtitle": "Google geschäftlich · schreibgeschützt",
                    "start": block.start_at,
                    "end": block.end_at,
                    "busy_end": block.end_at,
                    "kind": "external",
                    "cancelled": False,
                    "url": reverse("appointments:external", args=[block.pk]),
                }
            )
    return sorted(result, key=lambda row: (row["start"], row["end"]))


def day_rows(day, entries):
    start, end = midnight(day), midnight(day + timedelta(days=1))
    today = [
        item | {"display_start": max(item["start"], start), "display_end": min(item["end"], end)}
        for item in entries
        if item["start"] < end and item["end"] > start
    ]
    window_start = min(
        [datetime.combine(day, time(8), BERLIN)] + [item["display_start"] for item in today]
    )
    window_end = max(
        [datetime.combine(day, time(20), BERLIN)] + [min(item["busy_end"], end) for item in today]
    )
    busy = sorted(
        [
            (max(item["start"], window_start), min(item["busy_end"], end))
            for item in today
            if not item["cancelled"]
        ]
    )
    cursor = window_start
    free = []
    for a, b in busy + [(window_end, window_end)]:
        if a > cursor:
            free.append(
                {
                    "kind": "free",
                    "start": cursor,
                    "end": a,
                    "display_start": cursor,
                    "display_end": a,
                    "title": "Freie Zeit",
                    "url": reverse("appointments:create")
                    + "?datum="
                    + day.isoformat()
                    + "&beginn="
                    + timezone.localtime(cursor, BERLIN).strftime("%H:%M"),
                }
            )
        cursor = max(cursor, b)
    return sorted(today + free, key=lambda item: (item["display_start"], item["kind"] == "free"))


def month_days(day):
    return list(calendar.Calendar(firstweekday=0).itermonthdates(day.year, day.month))


def connections(user):
    existing = {row.role: row for row in CalendarConnection.objects.for_user(user)}
    return [
        existing.get(role) or CalendarConnection(role=role)
        for role in CalendarConnection.Role.values
    ]
