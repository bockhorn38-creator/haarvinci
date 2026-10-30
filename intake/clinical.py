"""Behandlungs-/Zahlungspakete: Vorschau mit den gleichen Formularen und Diensten."""

import uuid

from django import forms
from django.utils import timezone

from customers.models import Customer
from extensions.models import ExtensionPosition
from treatments.forms import PaymentForm, TreatmentForm
from treatments.models import ZERO, Payment, PriceOption, Treatment
from treatments.services import BusinessError, book_payment, quote, save_treatment

from .parser import ImportProblem


def entity_id(draft, user, ref):
    return uuid.uuid5(uuid.UUID(draft.payload["id"]), f"owner:{user.pk}:extension:{ref}")


class TreatmentChoice(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        from django.utils.formats import number_format

        return f"{obj} · offen {number_format(obj.outstanding, 2)} € · Vorgang {obj.pk.hex[:8]}"


def review_extra(draft, user, posted, plan, selected, problems):
    treatment_forms, payment_forms = [], []
    plan["treatments"], plan["payments"] = [], []
    targets = {}
    used_appointments = set()
    signatures = set()
    positions = {item["entity_ref"]: item for item in plan["extensions"]}
    appointments = {item["entity_ref"]: item for item in plan["appointments"]}
    for index, incoming in enumerate(draft.payload.get("treatments", [])):
        prefix = f"t{index}"
        customer = selected.get(incoming["customer_ref"])
        row = {"incoming": incoming, "ref": incoming["ref"], "existing": None, "quote": None}
        if incoming["mode"] == "existing":
            form = forms.Form(posted if posted is not None else {}, prefix=prefix)
            form.fields["target"] = TreatmentChoice(
                label="Bestehenden Behandlungsvorgang eindeutig auswählen",
                queryset=Treatment.objects.for_user(user).filter(customer=customer)
                if customer
                else Treatment.objects.none(),
            )
            valid = form.is_valid()
            existing = form.cleaned_data.get("target")
            if not customer:
                form.add_error(None, "Bitte zuerst eine vorhandene Kundenakte auswählen.")
                valid = False
            data = {}
            pricing = None
            row["existing"] = existing
        else:
            initial = dict(incoming["data"])
            initial.setdefault("price_mode", "weaving")
            initial.setdefault("status", "planned")
            chosen_services = []
            unknown = []
            for name in incoming["services"]:
                matches = [
                    s
                    for s in PriceOption.objects.for_user(user).filter(
                        category="service", active=True
                    )
                    if s.name.casefold() == name.casefold()
                ]
                if len(matches) != 1:
                    unknown.append(name)
                else:
                    chosen_services.append(str(matches[0].pk))
            initial["services"] = chosen_services
            bound = (
                posted
                if posted is not None
                else {f"{prefix}-{key}": value for key, value in initial.items()}
            )
            form = TreatmentForm(bound, prefix=prefix, user=user, customer=customer)
            form.fields.pop("customer")
            if incoming.get("appointment_ref"):
                form.fields.pop("appointment")
            valid = form.is_valid()
            data = dict(form.cleaned_data)
            if unknown:
                form.add_error(
                    "services",
                    "Nicht eindeutig in der Preisliste gefunden: "
                    + ", ".join(unknown)
                    + ". Bitte zuerst die Preisliste ergänzen oder den Importtext korrigieren.",
                )
                valid = False
            existing = None
            pricing = None
            extra_positions = []
            for ref in incoming["extension_refs"]:
                candidate = positions.get(ref)
                if candidate:
                    fake_customer = customer or Customer(owner=user)
                    extra_positions.append(
                        ExtensionPosition(
                            id=entity_id(draft, user, ref),
                            customer=fake_customer,
                            **{
                                k: candidate["data"][k] for k in candidate["data"] if k != "version"
                            },
                        )
                    )
                else:
                    form.add_error(None, "Bitte zuerst die referenzierten Extensions prüfen.")
                    valid = False
            data["extensions"] = list(data.get("extensions", [])) + extra_positions
            if len({p.pk for p in data["extensions"]}) != len(data["extensions"]):
                form.add_error("extensions", "Eine Extensions-Position wurde mehrfach ausgewählt.")
                valid = False
            linked = appointments.get(incoming.get("appointment_ref"))
            if incoming.get("appointment_ref"):
                if not linked:
                    form.add_error(None, "Bitte zuerst den referenzierten Termin prüfen.")
                    valid = False
                elif (
                    data.get("status") == "completed" and linked["data"]["end_at"] > timezone.now()
                ):
                    form.add_error("status", "Der verknüpfte Termin liegt noch in der Zukunft.")
                    valid = False
            key = incoming.get("appointment_ref") or str(getattr(data.get("appointment"), "pk", ""))
            if key:
                if key in used_appointments:
                    form.add_error(
                        None,
                        "Dieser Termin ist bereits einem anderen Behandlungsvorgang im Paket zugeordnet.",
                    )
                    valid = False
                used_appointments.add(key)
            if valid:
                try:
                    pricing = quote(user, data)
                    signature = (
                        str(customer.pk) if customer else incoming["customer_ref"],
                        data["performed_on"],
                        data["description"].casefold(),
                        pricing["total"],
                    )
                    if signature in signatures or (
                        customer
                        and Treatment.objects.for_user(user)
                        .filter(
                            customer=customer,
                            performed_on=data["performed_on"],
                            description__iexact=data["description"],
                        )
                        .exists()
                    ):
                        raise BusinessError(
                            "Ein entsprechender Behandlungsvorgang besteht bereits. Bitte im Import als existing eindeutig auswählen."
                        )
                    signatures.add(signature)
                    if (
                        data.get("appointment")
                        and Treatment.objects.filter(appointment=data["appointment"]).exists()
                    ):
                        raise BusinessError(
                            "Dieser Termin besitzt bereits einen Behandlungsvorgang."
                        )
                except BusinessError as error:
                    form.add_error(None, str(error))
                    valid = False
        row["form"], row["quote"] = form, pricing
        treatment_forms.append(row)
        if not valid:
            problems.append("Bitte Behandlungen, Preise und Zuordnungen prüfen.")
            continue
        entry = {
            "ref": incoming["ref"],
            "customer_ref": incoming["customer_ref"],
            "existing": existing,
            "version": existing.version if existing else None,
            "data": data,
            "quote": pricing,
            "appointment_ref": incoming.get("appointment_ref"),
            "extension_refs": incoming["extension_refs"],
        }
        plan["treatments"].append(entry)
        targets[incoming["ref"]] = entry
    balances = {
        ref: (entry["existing"].net_paid if entry["existing"] else ZERO)
        for ref, entry in targets.items()
    }
    target_key = {
        ref: (str(entry["existing"].pk) if entry["existing"] else ref)
        for ref, entry in targets.items()
    }
    balances = {target_key[ref]: value for ref, value in balances.items()}
    seen_payments = set()
    receipts = {}
    refunded = {}
    for index, incoming in enumerate(draft.payload.get("payments", [])):
        prefix = f"p{index}"
        target = targets.get(incoming["treatment_ref"])
        existing = target["existing"] if target else None
        refund = incoming["data"]["kind"] == "refund"
        initial = dict(incoming["data"])
        initial.setdefault("purpose", "refund" if refund else "partial")
        if refund:
            initial["purpose"] = "refund"
        bound = (
            posted
            if posted is not None
            else {f"{prefix}-{key}": value for key, value in initial.items()}
        )
        form = PaymentForm(
            bound, prefix=prefix, user=user, treatment=existing, refund=refund, imported=True
        )
        if refund and incoming.get("refund_of"):
            form.fields.pop("original")
        valid = form.is_valid()
        clean = dict(form.cleaned_data)
        if not target:
            form.add_error(
                None, "Bitte den zugehörigen Behandlungsvorgang zuerst eindeutig prüfen."
            )
            valid = False
        if valid:
            total = target["existing"].total if existing else target["quote"]["total"]
            balance = balances[target_key[incoming["treatment_ref"]]]
            if refund:
                original = (
                    receipts.get(incoming.get("refund_of"))
                    if incoming.get("refund_of")
                    else clean.get("original")
                )
                key = incoming.get("refund_of") or str(getattr(original, "pk", ""))
                available = (
                    original["amount"]
                    if isinstance(original, dict)
                    else original.refundable
                    if original
                    else ZERO
                ) - refunded.get(key, ZERO)
                if clean["amount"] > available or not original:
                    form.add_error(
                        "amount",
                        "Die Erstattung übersteigt den verbleibenden ursprünglichen Zahlungseingang oder die Zuordnung fehlt.",
                    )
                    valid = False
                else:
                    balances[target_key[incoming["treatment_ref"]]] -= clean["amount"]
                    refunded[key] = refunded.get(key, ZERO) + clean["amount"]
            elif (existing and existing.status == "cancelled") or clean["amount"] > total - balance:
                form.add_error(
                    "amount",
                    "Der Betrag übersteigt den offenen Restbetrag oder der Vorgang ist storniert.",
                )
                valid = False
            else:
                balances[target_key[incoming["treatment_ref"]]] += clean["amount"]
                receipts[incoming["ref"]] = {"amount": clean["amount"]}
        if valid:
            fingerprint = (
                target_key[incoming["treatment_ref"]],
                incoming["data"]["kind"],
                clean["amount"],
                clean["booked_on"],
                clean["method"],
                clean["purpose"],
                clean.get("notes", ""),
            )
            duplicate = (
                existing
                and Payment.objects.for_user(user)
                .filter(
                    treatment=existing,
                    state="posted",
                    kind=incoming["data"]["kind"],
                    amount=clean["amount"],
                    booked_on=clean["booked_on"],
                    method=clean["method"],
                    purpose=clean["purpose"],
                    notes=clean.get("notes", ""),
                )
                .exists()
            )
            if fingerprint in seen_payments or duplicate:
                form.add_error(
                    None,
                    "Eine vollständig gleiche Geldbuchung ist bereits vorhanden oder im Paket doppelt enthalten. Bitte prüfen; echte weitere Zahlungen im normalen Vorgang eindeutig dokumentieren.",
                )
                valid = False
            seen_payments.add(fingerprint)
        payment_forms.append({"incoming": incoming, "form": form, "ref": incoming["ref"]})
        if valid:
            plan["payments"].append(
                {
                    "ref": incoming["ref"],
                    "treatment_ref": incoming["treatment_ref"],
                    "refund_of": incoming.get("refund_of"),
                    "refund": refund,
                    "data": clean,
                }
            )
        else:
            problems.append("Bitte Geldbeträge und Zahlungszuordnungen prüfen.")
    return {"treatments": treatment_forms, "payments": payment_forms}


def commit_extra(draft, user, resolved, extensions, appointments, counts):
    from .parser import canonical

    # Vor Änderungen alle ausgewählten bestehenden Finanzstände gegen die Vorschau prüfen.
    treatment_targets = {}
    for incoming in draft.plan.get("treatments", []):
        if incoming["existing"]:
            current = (
                Treatment.objects.for_user(user).select_for_update().get(pk=incoming["existing"].pk)
            )
            if (
                current.version != incoming["version"]
                or current.customer_id != resolved[incoming["customer_ref"]].pk
            ):
                raise ImportProblem(
                    "Ein ausgewählter Behandlungsvorgang wurde inzwischen geändert. Bitte erneut prüfen."
                )
            treatment_targets[incoming["ref"]] = current
    for incoming in draft.plan.get("treatments", []):
        if incoming["existing"]:
            continue
        data = dict(incoming["data"])
        data["customer"] = resolved[incoming["customer_ref"]]
        if incoming["appointment_ref"]:
            data["appointment"] = appointments[incoming["appointment_ref"]]
        ids = [p.pk for p in data["extensions"]]
        data["extensions"] = list(ExtensionPosition.objects.for_user(user).filter(pk__in=ids))
        if len(data["extensions"]) != len(ids):
            raise ImportProblem("Eine gewählte Extensions-Position ist nicht mehr verfügbar.")
        current_signature = {
            "performed_on": data["performed_on"],
            "description__iexact": data["description"],
        }
        if (
            Treatment.objects.for_user(user)
            .filter(customer=data["customer"], **current_signature)
            .exists()
        ):
            raise ImportProblem(
                "Ein entsprechender Behandlungsvorgang wurde inzwischen angelegt. Bitte neu zuordnen."
            )
        # Gleiche Reihenfolge wie in der Vorschau ist Teil der Preis-Momentaufnahme.
        order = {key: index for index, key in enumerate(ids)}
        data["extensions"].sort(key=lambda p: order[p.pk])
        item = save_treatment(user=user, data=data, expected_quote=incoming["quote"]["digest"])
        treatment_targets[incoming["ref"]] = item
        counts["treatments"] += 1
    booked = {}
    for incoming in draft.plan.get("payments", []):
        item = treatment_targets[incoming["treatment_ref"]]
        item.refresh_from_db()
        data = dict(incoming["data"])
        data["version"] = item.version
        data["booking_key"] = uuid.uuid5(
            uuid.UUID(draft.payload["id"]), f"owner:{user.pk}:payment:{incoming['ref']}"
        )
        if incoming["refund_of"]:
            data["original"] = booked[incoming["refund_of"]]
        if (
            Payment.objects.for_user(user)
            .filter(
                treatment=item,
                state="posted",
                kind="refund" if incoming["refund"] else "receipt",
                amount=data["amount"],
                booked_on=data["booked_on"],
                method=data["method"],
                purpose=data["purpose"],
                notes=data.get("notes", ""),
            )
            .exists()
        ):
            raise ImportProblem(
                "Eine gleiche Geldbuchung wurde inzwischen angelegt. Bitte den Vorgang erneut prüfen."
            )
        booked[incoming["ref"]] = book_payment(
            user=user, treatment_id=item.pk, data=data, refund=incoming["refund"]
        )
        counts["payments"] += 1
    return canonical(counts)
