"""Fachregeln und Sperren für Preise, Vorgänge und Geld; keine Float-Beträge."""

import hashlib
import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from appointments.models import Appointment
from customers.models import Customer, CustomerEvent
from customers.services import EditConflict
from extensions.forms import POSITION_FIELDS
from extensions.models import ExtensionPosition

from .models import MAX_MONEY, ZERO, Payment, PriceLine, PriceOption, Treatment, TreatmentExtension


class BusinessError(Exception):
    pass


def owner_lock(user):
    get_user_model().objects.select_for_update().get(pk=user.pk)


def money(value):
    try:
        value = Decimal(str(value))
        if (
            not value.is_finite()
            or value < 0
            or value > MAX_MONEY
            or value != value.quantize(Decimal(".01"))
        ):
            raise ValueError
    except (ValueError, ArithmeticError):
        raise BusinessError(
            "Bitte einen gültigen Eurobetrag mit höchstens zwei Nachkommastellen angeben."
        ) from None
    return value


def quote(user, data, instance=None):
    lines = []
    selected = list(data.get("services", []))
    positions = list(data.get("extensions", []))
    if len(selected) > 50 or len(positions) > 50:
        raise BusinessError(
            "Pro Behandlung sind höchstens 50 Zusatzleistungen und 50 Extensions-Positionen möglich."
        )
    if any(p.customer.owner_id != user.pk for p in positions):
        raise BusinessError("Ungültige Extensions-Zuordnung.")
    if instance and data["price_mode"] == "keep":
        old_services = set(
            instance.lines.exclude(source=None)
            .filter(source__category="service")
            .values_list("source_id", flat=True)
        )
        if (
            data.get("rows") != instance.rows
            or {p.pk for p in selected} != old_services
            or bool(data.get("charge_extensions")) != instance.charge_extensions
            or set(p.pk for p in positions)
            != set(
                instance.extension_links.exclude(position=None).values_list(
                    "position_id", flat=True
                )
            )
        ):
            raise BusinessError(
                "Für geänderte Reihen, Leistungen oder Extensions bitte den Preis bewusst neu berechnen oder einen individuellen Gesamtpreis wählen."
            )
        lines = [
            {
                "label": line.label,
                "amount": str(line.amount),
                "source": str(line.source_id) if line.source_id else None,
            }
            for line in instance.lines.all()
        ]
    else:
        if data.get("rows"):
            tariff = (
                PriceOption.objects.for_user(user)
                .filter(category="weaving", rows=data["rows"], active=True)
                .first()
            )
            if not tariff and data["price_mode"] == "weaving":
                raise BusinessError(
                    "Für diese Reihenanzahl fehlt ein aktiver Gesamtpreis. Bitte zuerst die Preisliste ergänzen."
                )
            if tariff:
                lines.append(
                    {
                        "label": f"Weaving · {tariff.rows} Reihen · {tariff.name}",
                        "amount": str(tariff.price),
                        "source": str(tariff.pk),
                        "version": tariff.version,
                    }
                )
        elif data["price_mode"] == "weaving":
            raise BusinessError("Die Reihenanzahl fehlt.")
        for service in selected:
            current = (
                PriceOption.objects.for_user(user)
                .filter(pk=service.pk, category="service", active=True)
                .first()
            )
            if not current:
                raise BusinessError(
                    "Eine Zusatzleistung ist nicht mehr verfügbar. Bitte neu auswählen."
                )
            lines.append(
                {
                    "label": current.name,
                    "amount": str(current.price),
                    "source": str(current.pk),
                    "version": current.version,
                }
            )
        if data.get("charge_extensions"):
            for position in positions:
                current = (
                    position
                    if position._state.adding
                    else ExtensionPosition.objects.for_user(user).get(pk=position.pk)
                )
                if current.sale_price is None:
                    raise BusinessError(
                        "Für mindestens eine gewählte Extensions-Position fehlt ein Verkaufspreis."
                    )
                lines.append(
                    {
                        "label": f"Extensions · {current}",
                        "amount": str(current.sale_price),
                        "source": None,
                        "position": str(current.pk),
                        "version": current.version,
                    }
                )
        subtotal = sum((Decimal(line["amount"]) for line in lines), ZERO)
        if data["price_mode"] == "individual":
            total = money(data.get("custom_price"))
            lines.append(
                {
                    "label": "Individuelle Preisvereinbarung (Gesamtpreis)",
                    "amount": str(total - subtotal),
                    "source": None,
                }
            )
    total = sum((Decimal(line["amount"]) for line in lines), ZERO)
    money(total)
    payload = {
        "lines": lines,
        "total": str(total),
        "rows": data.get("rows"),
        "mode": data["price_mode"],
        "extensions": [(str(p.pk), p.version) for p in positions],
        "charge_extensions": bool(data.get("charge_extensions")),
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return {"lines": lines, "total": total, "digest": digest}


def event(item, kind, summary, snapshot=None):
    CustomerEvent.objects.create(
        customer=item.customer,
        actor=item.owner,
        kind=kind,
        occurred_on=timezone.localdate(),
        treatment_uuid=item.pk,
        summary=summary[:500],
        snapshot=snapshot
        or {
            "Behandlung": item.description,
            "Datum": str(item.performed_on),
            "Status": item.get_status_display(),
            "Gesamtpreis (€)": str(item.total),
            "Dokumentation": item.notes,
            "Reihen": str(item.rows or ""),
            "Stornogrund": item.cancelled_reason,
            "Extensions": "; ".join(item.extension_links.values_list("label", flat=True)),
        },
    )


@transaction.atomic
def save_treatment(*, user, data, treatment_id=None, expected_quote=None):
    owner_lock(user)
    item = (
        Treatment.objects.for_user(user).select_for_update().get(pk=treatment_id)
        if treatment_id
        else Treatment(owner=user)
    )
    if treatment_id and item.version != data.get("version"):
        raise EditConflict
    if treatment_id and item.status == "cancelled":
        raise BusinessError(
            "Ein stornierter Vorgang bleibt unverändert. Bitte bei Bedarf einen neuen Vorgang anlegen."
        )
    customer = Customer.objects.for_user(user).select_for_update().get(pk=data["customer"].pk)
    if treatment_id and customer.pk != item.customer_id:
        raise BusinessError(
            "Ein Behandlungsvorgang kann nicht auf eine andere Kundin übertragen werden."
        )
    appointment = data.get("appointment")
    if appointment:
        appointment = Appointment.objects.for_user(user).select_for_update().get(pk=appointment.pk)
        if appointment.customer_id != customer.pk or appointment.status == "cancelled":
            raise BusinessError(
                "Termin und Behandlung müssen zur selben Kundin gehören; abgesagte Termine zuerst prüfen."
            )
        if Treatment.objects.filter(appointment=appointment).exclude(pk=item.pk).exists():
            raise BusinessError(
                "Zu diesem Termin besteht bereits ein Behandlungsvorgang. Bitte diesen öffnen."
            )
    if (
        treatment_id
        and item.appointment_id != (appointment.pk if appointment else None)
        and item.payments.exists()
    ):
        raise BusinessError("Bei bestehenden Geldbuchungen bleibt die Terminzuordnung fest.")
    positions = list(data.get("extensions", []))
    if any(p.customer_id != customer.pk for p in positions):
        raise BusinessError("Die gewählten Extensions gehören nicht zu dieser Kundin.")
    if (
        data["status"] not in ["planned", "completed"]
        or not 2000 <= data["performed_on"].year <= 2100
    ):
        raise BusinessError("Ungültiger Status oder ungültiges Behandlungsdatum.")
    if data["status"] == "completed" and (
        data["performed_on"] > timezone.localdate()
        or (appointment and appointment.end_at > timezone.now())
    ):
        raise BusinessError("Eine zukünftige Behandlung kann noch nicht durchgeführt sein.")
    pricing = quote(user, data, item if treatment_id else None)
    if expected_quote and pricing["digest"] != expected_quote:
        raise BusinessError(
            "Preise oder Zuordnungen wurden inzwischen geändert. Bitte die Preisübersicht erneut prüfen."
        )
    if treatment_id and item.net_paid > pricing["total"]:
        raise BusinessError(
            "Der neue Gesamtpreis liegt unter den bereits verbuchten Zahlungen. Bitte zuerst die erforderliche Erstattung erfassen."
        )
    for field in ["performed_on", "description", "status", "rows", "notes", "charge_extensions"]:
        setattr(item, field, data.get(field, False if field == "charge_extensions" else ""))
    item.customer, item.appointment, item.total = customer, appointment, pricing["total"]
    if data["price_mode"] != "keep":
        item.price_mode = data["price_mode"]
    item.version = item.version + 1 if treatment_id else 1
    item.full_clean(exclude=["id"])
    item.save()
    if data["price_mode"] != "keep":
        item.lines.all().delete()
        PriceLine.objects.bulk_create(
            [
                PriceLine(
                    treatment=item,
                    source_id=line.get("source"),
                    label=line["label"][:300],
                    amount=Decimal(line["amount"]),
                    order=index,
                )
                for index, line in enumerate(pricing["lines"])
            ]
        )
        item.extension_links.all().delete()
        TreatmentExtension.objects.bulk_create(
            [
                TreatmentExtension(
                    treatment=item,
                    position=p,
                    position_uuid=p.pk,
                    label=str(p),
                    snapshot={
                        key: str(getattr(p, key)) if getattr(p, key) is not None else ""
                        for key in POSITION_FIELDS
                    },
                )
                for p in positions
            ]
        )
    if data["status"] == "completed" and appointment and appointment.status != "completed":
        from appointments.services import EDITABLE, save_appointment

        save_appointment(
            user=user,
            appointment_id=appointment.pk,
            data={key: getattr(appointment, key) for key in EDITABLE}
            | {"status": "completed", "version": appointment.version, "allow_overlap": True},
        )
    event(
        item,
        "treatment_updated" if treatment_id else "treatment_created",
        f"{item.get_status_display()}: {item.description}",
    )
    return item


@transaction.atomic
def cancel_treatment(*, user, treatment_id, version, reason):
    owner_lock(user)
    item = Treatment.objects.for_user(user).select_for_update().get(pk=treatment_id)
    if item.status == "cancelled":
        return item
    if item.version != version:
        raise EditConflict
    if not reason.strip():
        raise BusinessError("Bitte einen Stornogrund angeben.")
    item.status, item.cancelled_reason = "cancelled", reason.strip()
    item.version += 1
    item.save()
    event(item, "treatment_cancelled", f"Behandlung storniert: {reason}")
    return item


@transaction.atomic
def book_payment(*, user, treatment_id, data, refund=False):
    owner_lock(user)
    item = Treatment.objects.for_user(user).select_for_update().get(pk=treatment_id)
    prior = Payment.objects.for_user(user).filter(booking_key=data["booking_key"]).first()
    amount = money(data["amount"])
    kind = "refund" if refund else "receipt"
    if prior:
        if (
            prior.treatment_id != item.pk
            or prior.kind != kind
            or prior.amount != amount
            or prior.booked_on != data["booked_on"]
            or prior.method != data["method"]
            or prior.purpose != data["purpose"]
            or prior.notes != data.get("notes", "")
            or prior.original_id != (getattr(data.get("original"), "pk", None) if refund else None)
        ):
            raise BusinessError("Diese Buchungskennung wurde bereits für andere Angaben verwendet.")
        return prior
    if data.get("version") != item.version:
        raise EditConflict
    if amount <= 0 or data["booked_on"] > timezone.localdate():
        raise BusinessError(
            "Bitte einen positiven Betrag und ein tatsächliches Zahlungsdatum angeben."
        )
    original = None
    if refund:
        original = (
            Payment.objects.for_user(user)
            .select_for_update()
            .get(pk=data["original"].pk, treatment=item, kind="receipt", state="posted")
        )
        if amount > original.refundable or not data.get("notes", "").strip():
            raise BusinessError(
                "Die Erstattung überschreitet den noch erstattbaren Zahlungseingang oder ihr Grund fehlt."
            )
    elif item.status == "cancelled" or amount > item.outstanding:
        raise BusinessError(
            "Der Zahlungseingang überschreitet den offenen Betrag oder der Vorgang ist storniert."
        )
    if not refund and data["purpose"] == "final" and amount != item.outstanding:
        raise BusinessError(
            "Eine Restzahlung muss dem gesamten noch offenen Betrag entsprechen. Für einen Teilbetrag bitte Teilzahlung wählen."
        )
    if data["purpose"] not in (["refund"] if refund else ["deposit", "partial", "final"]):
        raise BusinessError("Ungültige Buchungsart.")
    entry = Payment(
        owner=user,
        treatment=item,
        booking_key=data["booking_key"],
        kind=kind,
        purpose=data["purpose"],
        amount=amount,
        booked_on=data["booked_on"],
        method=data["method"],
        original=original,
        notes=data.get("notes", ""),
    )
    entry.full_clean()
    entry.save()
    item.version += 1
    item.save(update_fields=["version", "updated_at"])
    event(
        item,
        "payment_refunded" if refund else "payment_received",
        f"{entry.get_purpose_display()}: {amount:.2f} € · {item.description}",
        {
            "Buchung": str(entry.pk),
            "Art": entry.get_purpose_display(),
            "Betrag (€)": str(amount),
            "Zahlungsdatum": str(entry.booked_on),
            "Zahlungsweg": entry.get_method_display(),
            "Notiz": entry.notes,
        },
    )
    return entry


@transaction.atomic
def void_payment(*, user, payment_id, version, reason):
    owner_lock(user)
    entry = (
        Payment.objects.for_user(user)
        .select_for_update()
        .select_related("treatment")
        .get(pk=payment_id)
    )
    item = Treatment.objects.for_user(user).select_for_update().get(pk=entry.treatment_id)
    if entry.state == "voided":
        return entry
    if item.version != version:
        raise EditConflict
    if not reason.strip():
        raise BusinessError("Bitte den Grund der Buchungskorrektur angeben.")
    if entry.kind == "receipt" and entry.refunds.filter(state="posted").exists():
        raise BusinessError(
            "Zuerst die zugehörigen Erstattungsbuchungen prüfen und gegebenenfalls korrigieren."
        )
    if (
        entry.kind == "refund"
        and item.status != "cancelled"
        and item.net_paid + entry.amount > item.total
    ):
        raise BusinessError(
            "Die Korrektur würde zu einer Überzahlung führen. Bitte zuerst den Vorgang prüfen."
        )
    entry.state, entry.void_reason = "voided", reason.strip()
    entry.save(update_fields=["state", "void_reason"])
    item.version += 1
    item.save(update_fields=["version", "updated_at"])
    event(
        item,
        "payment_voided",
        f"Buchung storniert: {reason}",
        {"Buchung": str(entry.pk), "Betrag (€)": str(entry.amount), "Grund": reason},
    )
    return entry


def on_appointment_cancelled(appointment):
    item = Treatment.objects.filter(appointment=appointment, status="planned").first()
    if item:
        cancel_treatment(
            user=appointment.owner,
            treatment_id=item.pk,
            version=item.version,
            reason="Der verknüpfte Termin wurde abgesagt.",
        )
