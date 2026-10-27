from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods

from customers.models import Customer
from customers.services import EditConflict

from .forms import AppointmentForm, GoogleSettingsForm, TypeForm, berlin_time
from .models import Appointment, CalendarSettings, RemoteBusinessEvent
from .presentation import connections, day_rows, entries_for_range, midnight, month_days
from .services import ScheduleConflict, cancel_appointment, conflicts, save_appointment


def customer_for_query(user, value):
    try:
        key = UUID(value)
    except (ValueError, TypeError):
        raise Http404 from None
    return get_object_or_404(Customer.objects.for_user(user), pk=key)


def selected_day(value):
    try:
        result = date.fromisoformat(value)
        if not 2001 <= result.year <= 2099:
            raise ValueError
        return result
    except (ValueError, TypeError):
        return timezone.localdate()


@login_required
@require_GET
def calendar_view(request):
    day = selected_day(request.GET.get("datum"))
    mode = request.GET.get("ansicht", "woche")
    if mode not in ["tag", "woche", "monat"]:
        mode = "woche"
    customer = (
        customer_for_query(request.user, request.GET["kundin"])
        if request.GET.get("kundin")
        else None
    )
    if mode == "monat":
        dates = month_days(day)
        first, last = dates[0], dates[-1]
        prev = (day.replace(day=1) - timedelta(days=1)).replace(day=1)
        nxt = (day.replace(day=28) + timedelta(days=4)).replace(day=1)
    else:
        first = day if mode == "tag" else day - timedelta(days=day.weekday())
        dates = [first + timedelta(days=index) for index in range(1 if mode == "tag" else 7)]
        last = dates[-1]
        prev, nxt = day - timedelta(days=len(dates)), day + timedelta(days=len(dates))
    entries = entries_for_range(request.user, first, last, customer)
    days = [
        {
            "date": current,
            "is_today": current == timezone.localdate(),
            "other_month": current.month != day.month,
            "entries": [
                entry
                for entry in entries
                if entry["start"] < midnight(current + timedelta(days=1))
                and entry["end"] > midnight(current)
            ],
            "rows": day_rows(current, entries),
        }
        for current in dates
    ]
    return render(
        request,
        "appointments/calendar.html",
        {
            "nav": "calendar",
            "mode": mode,
            "day": day,
            "days": days,
            "previous": prev,
            "next": nxt,
            "connections": connections(request.user),
            "customer_filter": customer,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def appointment_form(request, pk=None):
    item = get_object_or_404(Appointment.objects.for_user(request.user), pk=pk) if pk else None
    initial = {"day": selected_day(request.GET.get("datum")), "begin": "09:00", "finish": "10:00"}
    if request.GET.get("beginn"):
        try:
            clock = datetime.strptime(request.GET["beginn"], "%H:%M")
            initial.update(begin=clock.time(), finish=(clock + timedelta(minutes=60)).time())
        except ValueError:
            pass
    if request.GET.get("kundin"):
        initial["customer"] = customer_for_query(request.user, request.GET["kundin"])
    form = AppointmentForm(
        request.POST if request.method == "POST" else None,
        user=request.user,
        instance=item,
        initial=initial if not item else None,
    )
    status, overlap = 200, []
    if request.method == "POST" and form.is_valid():
        try:
            item = save_appointment(user=request.user, data=form.cleaned_data, appointment_id=pk)
        except EditConflict:
            form.add_error(
                None,
                "Dieser Termin wurde inzwischen geändert. Deine Eingaben bleiben sichtbar. Bitte öffne den aktuellen Termin erneut.",
            )
            status = 409
        except Appointment.DoesNotExist as error:
            raise Http404 from error
        except ScheduleConflict as error:
            overlap = error.entries
            form.add_error(
                None,
                "Die Zeit überschneidet sich mit einer vorhandenen Belegung. Bitte verschiebe den Termin oder bestätige die Überschneidung ausdrücklich.",
            )
        else:
            messages.success(request, "Der Termin wurde gespeichert.")
            return redirect("appointments:detail", pk=item.pk)
    return render(
        request,
        "appointments/form.html",
        {
            "nav": "calendar",
            "form": form,
            "appointment": item,
            "editing": bool(pk),
            "overlaps": overlap,
        },
        status=status,
    )


@login_required
@require_GET
def appointment_detail(request, pk):
    item = get_object_or_404(
        Appointment.objects.for_user(request.user).select_related("customer", "appointment_type"),
        pk=pk,
    )
    overlap = (
        []
        if item.status == "cancelled"
        else conflicts(
            user=request.user,
            start=item.start_at,
            end=item.end_at,
            buffer=item.buffer_minutes,
            exclude=item.pk,
        )
    )
    return render(
        request,
        "appointments/detail.html",
        {"nav": "calendar", "appointment": item, "overlaps": overlap},
    )


class VersionForm(forms.Form):
    version = forms.IntegerField(min_value=1, widget=forms.HiddenInput)


@login_required
@require_http_methods(["GET", "POST"])
def appointment_cancel(request, pk):
    item = get_object_or_404(Appointment.objects.for_user(request.user), pk=pk)
    form = VersionForm(
        request.POST if request.method == "POST" else None, initial={"version": item.version}
    )
    status = 200
    if request.method == "POST" and form.is_valid():
        try:
            cancel_appointment(
                user=request.user, appointment_id=pk, version=form.cleaned_data["version"]
            )
        except EditConflict:
            form.add_error(
                None,
                "Der Termin wurde inzwischen geändert. Bitte prüfe den aktuellen Stand erneut.",
            )
            status = 409
        else:
            messages.success(request, "Der Termin wurde abgesagt. Er zählt nicht als Besuch.")
            return redirect("appointments:detail", pk=pk)
    return render(
        request,
        "appointments/cancel.html",
        {"nav": "calendar", "appointment": item, "form": form},
        status=status,
    )


@login_required
@require_GET
def external_detail(request, pk):
    item = get_object_or_404(
        RemoteBusinessEvent.objects.filter(connection__owner=request.user), pk=pk
    )
    return render(request, "appointments/external.html", {"nav": "calendar", "item": item})


@login_required
@require_GET
def customer_appointments(request, pk):
    customer = get_object_or_404(Customer.objects.for_user(request.user), pk=pk)
    items = customer.appointments.order_by("-start_at").select_related("appointment_type")
    return render(
        request,
        "appointments/customer_list.html",
        {
            "nav": "calendar",
            "customer": customer,
            "page": Paginator(items, 20).get_page(request.GET.get("seite")),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def google_settings(request):
    settings, _ = CalendarSettings.objects.get_or_create(owner=request.user)
    form = GoogleSettingsForm(request.POST if request.method == "POST" else None, instance=settings)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Die Adresse des Anmeldedienstes wurde gespeichert.")
        return redirect("appointments:google")
    return render(
        request,
        "appointments/google.html",
        {
            "nav": "calendar",
            "form": form,
            "connections": connections(request.user),
            "configured": bool(settings.broker_url),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def type_create(request):
    form = TypeForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        item.owner = request.user
        item.save()
        messages.success(request, "Die neue Terminart steht ab jetzt zur Auswahl.")
        return redirect("appointments:create")
    return render(request, "appointments/type.html", {"nav": "calendar", "form": form})


@login_required
@require_GET
def duration(request):
    try:
        day = date.fromisoformat(request.GET.get("datum", ""))
        end_day = date.fromisoformat(request.GET.get("enddatum") or day.isoformat())
        start = berlin_time(day, time.fromisoformat(request.GET.get("beginn", "")))
        end = berlin_time(end_day, time.fromisoformat(request.GET.get("ende", "")))
        minutes = int((end.astimezone(UTC) - start.astimezone(UTC)).total_seconds() // 60)
        if not 0 < minutes <= 1440:
            raise ValueError
        return JsonResponse({"minutes": minutes})
    except (ValueError, forms.ValidationError):
        return JsonResponse(
            {"error": "Bitte gültige, eindeutige Uhrzeiten für Europe/Berlin wählen."}, status=400
        )
