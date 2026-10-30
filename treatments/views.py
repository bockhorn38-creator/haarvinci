import uuid

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods

from appointments.models import Appointment
from customers.models import Customer
from customers.services import EditConflict

from .forms import DecisionForm, PaymentForm, PriceForm, TreatmentForm
from .models import Payment, PriceOption, Treatment
from .reports import report
from .services import (
    BusinessError,
    book_payment,
    cancel_treatment,
    owner_lock,
    quote,
    save_treatment,
    void_payment,
)


class RangeForm(forms.Form):
    start = forms.DateField(
        label="Von",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )
    end = forms.DateField(
        label="Bis",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )

    def clean(self):
        data = super().clean()
        if data.get("start") and data.get("end") and data["end"] < data["start"]:
            self.add_error("end", "Das Ende muss nach dem Beginn liegen.")
        return data


@login_required
@require_GET
def overview(request):
    person = (
        get_object_or_404(Customer.objects.for_user(request.user), pk=request.GET["kundin"])
        if request.GET.get("kundin")
        else None
    )
    stats = report(request.user, customer=person)
    return render(
        request, "treatments/list.html", {"nav": "treatments", "stats": stats, "customer": person}
    )


@login_required
@require_GET
def statistics(request):
    form = RangeForm(request.GET or None)
    dates = form.cleaned_data if form.is_valid() else {}
    return render(
        request,
        "treatments/statistics.html",
        {
            "nav": "statistics",
            "stats": report(request.user, start=dates.get("start"), end=dates.get("end"))
            if not form.errors
            else None,
            "form": form,
        },
    )


@login_required
@require_GET
def detail(request, pk):
    item = get_object_or_404(
        Treatment.objects.for_user(request.user).select_related("customer", "appointment"), pk=pk
    )
    return render(
        request,
        "treatments/detail.html",
        {"nav": "treatments", "item": item, "payments": item.payments.all()},
    )


@login_required
@require_http_methods(["GET", "POST"])
def treatment_form(request, pk=None):
    item = get_object_or_404(Treatment.objects.for_user(request.user), pk=pk) if pk else None
    person = (
        item.customer
        if item
        else (
            get_object_or_404(Customer.objects.for_user(request.user), pk=request.GET["kundin"])
            if request.GET.get("kundin")
            else None
        )
    )
    appointment = (
        get_object_or_404(Appointment.objects.for_user(request.user), pk=request.GET["termin"])
        if request.GET.get("termin") and not item
        else None
    )
    if appointment:
        person = appointment.customer
        if hasattr(appointment, "treatment"):
            return redirect("treatments:detail", pk=appointment.treatment.pk)
    initial = {
        "customer": person,
        "appointment": appointment,
        "performed_on": timezone.localdate(appointment.start_at)
        if appointment
        else timezone.localdate(),
        "description": str(appointment.appointment_type) if appointment else "Weaving",
        "status": "completed" if appointment and appointment.status == "completed" else "planned",
        "price_mode": "weaving",
    }
    if person:
        initial["extensions"] = list(
            person.extensions.exclude(delivery_status="cancelled").values_list("pk", flat=True)
        )
    if item:
        initial.update(
            {
                field: getattr(item, field)
                for field in [
                    "customer",
                    "appointment",
                    "performed_on",
                    "description",
                    "status",
                    "rows",
                    "notes",
                    "charge_extensions",
                    "version",
                ]
            }
        )
        initial.update(
            price_mode="keep",
            custom_price=item.total,
            extensions=list(
                item.extension_links.exclude(position=None).values_list("position_id", flat=True)
            ),
            services=list(
                item.lines.exclude(source=None)
                .filter(source__category="service")
                .values_list("source_id", flat=True)
            ),
        )
    form = TreatmentForm(
        request.POST if request.method == "POST" else None,
        user=request.user,
        customer=person,
        instance=item,
        initial=initial,
    )
    pricing = None
    if request.method == "POST" and form.is_valid():
        try:
            pricing = quote(request.user, form.cleaned_data, item)
            if request.POST.get("action") == "save":
                if not form.cleaned_data["quote_digest"]:
                    raise BusinessError(
                        "Bitte zuerst den Preis prüfen und anschließend bestätigen."
                    )
                saved = save_treatment(
                    user=request.user,
                    data=form.cleaned_data,
                    treatment_id=item.pk if item else None,
                    expected_quote=form.cleaned_data["quote_digest"],
                )
                messages.success(request, "Behandlung und Preisvereinbarung gespeichert.")
                return redirect("treatments:detail", pk=saved.pk)
        except (BusinessError, EditConflict, ValidationError, IntegrityError) as error:
            form.add_error(
                None,
                str(error)
                if not isinstance(error, (EditConflict, IntegrityError))
                else "Der Vorgang wurde inzwischen geändert oder ist bereits verknüpft. Bitte erneut prüfen.",
            )
            pricing = None
    return render(
        request,
        "treatments/form.html",
        {"nav": "treatments", "form": form, "item": item, "customer": person, "pricing": pricing},
    )


@login_required
@require_http_methods(["GET", "POST"])
def payment_form(request, pk, refund=False):
    item = get_object_or_404(Treatment.objects.for_user(request.user), pk=pk)
    initial = {
        "booked_on": timezone.localdate(),
        "method": "cash",
        "purpose": "refund"
        if refund
        else ("deposit" if item.net_paid == 0 and item.status == "planned" else "partial"),
        "amount": item.refund_due if refund else item.outstanding,
        "version": item.version,
        "booking_key": uuid.uuid4(),
    }
    if refund:
        original = next(
            (
                entry
                for entry in item.payments.filter(kind="receipt", state="posted")
                if entry.refundable > 0
            ),
            None,
        )
        if original:
            initial.update(original=original.pk, amount=min(item.net_paid, original.refundable))
    form = PaymentForm(
        request.POST if request.method == "POST" else None,
        user=request.user,
        treatment=item,
        refund=refund,
        initial=initial,
    )
    if request.method == "POST" and form.is_valid():
        try:
            book_payment(user=request.user, treatment_id=pk, data=form.cleaned_data, refund=refund)
        except (BusinessError, EditConflict, ValidationError, Payment.DoesNotExist) as error:
            form.add_error(
                None,
                str(error)
                if not isinstance(error, (EditConflict, Payment.DoesNotExist))
                else "Vorgang oder Zahlungsstand geändert. Bitte erneut öffnen und prüfen.",
            )
        else:
            messages.success(
                request,
                "Rückerstattung dokumentiert."
                if refund
                else "Zahlung dokumentiert. Der Restbetrag ist aktualisiert.",
            )
            return redirect("treatments:detail", pk=pk)
    return render(
        request,
        "treatments/payment.html",
        {"nav": "treatments", "form": form, "item": item, "refund": refund},
    )


@login_required
@require_http_methods(["GET", "POST"])
def cancel(request, pk):
    item = get_object_or_404(Treatment.objects.for_user(request.user), pk=pk)
    form = DecisionForm(
        request.POST if request.method == "POST" else None, initial={"version": item.version}
    )
    if request.method == "POST" and form.is_valid():
        try:
            cancel_treatment(
                user=request.user,
                treatment_id=pk,
                version=form.cleaned_data["version"],
                reason=form.cleaned_data["reason"],
            )
        except (BusinessError, EditConflict) as error:
            form.add_error(
                None, str(error) or "Der Vorgang wurde inzwischen geändert. Bitte erneut öffnen."
            )
        else:
            messages.success(
                request,
                "Behandlung storniert. Bereits erhaltenes Geld gegebenenfalls gesondert zurückerstatten.",
            )
            return redirect("treatments:detail", pk=pk)
    return render(
        request,
        "treatments/decision.html",
        {"nav": "treatments", "form": form, "item": item, "void": False},
    )


@login_required
@require_http_methods(["GET", "POST"])
def payment_void(request, pk):
    entry = get_object_or_404(
        Payment.objects.for_user(request.user).select_related("treatment"), pk=pk
    )
    form = DecisionForm(
        request.POST if request.method == "POST" else None,
        initial={"version": entry.treatment.version},
    )
    if request.method == "POST" and form.is_valid():
        try:
            void_payment(
                user=request.user,
                payment_id=pk,
                version=form.cleaned_data["version"],
                reason=form.cleaned_data["reason"],
            )
        except (BusinessError, EditConflict) as error:
            form.add_error(
                None, str(error) or "Der Vorgang wurde inzwischen geändert. Bitte erneut öffnen."
            )
        else:
            messages.success(request, "Fehlerhafte Buchung nachvollziehbar storniert.")
            return redirect("treatments:detail", pk=entry.treatment_id)
    return render(
        request,
        "treatments/decision.html",
        {"nav": "treatments", "form": form, "item": entry.treatment, "entry": entry, "void": True},
    )


@login_required
@require_http_methods(["GET", "POST"])
def prices(request, pk=None):
    item = (
        get_object_or_404(PriceOption.objects.for_user(request.user), pk=pk)
        if pk
        else PriceOption(owner=request.user)
    )
    form = PriceForm(request.POST if request.method == "POST" else None, instance=item)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                owner_lock(request.user)
                if pk:
                    current = (
                        PriceOption.objects.for_user(request.user).select_for_update().get(pk=pk)
                    )
                    if current.version != form.cleaned_data.get("version"):
                        raise EditConflict
                    item.version = current.version + 1
                item.full_clean()
                item.save()
        except (EditConflict, ValidationError, IntegrityError):
            form.add_error(
                None,
                "Dieser Preisstand wurde inzwischen geändert oder die Reihenanzahl ist bereits belegt. Bitte prüfen.",
            )
        else:
            messages.success(
                request, "Preis gespeichert. Bestehende Preisvereinbarungen bleiben erhalten."
            )
            return redirect("treatments:prices")
    return render(
        request,
        "treatments/prices.html",
        {
            "nav": "treatments",
            "form": form,
            "item": item,
            "options": PriceOption.objects.for_user(request.user),
        },
    )
