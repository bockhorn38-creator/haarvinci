"""Vorschauen nur im RAM; fachliche Speicherung nach ausdrücklichem POST, atomar."""

import copy
import hashlib
import secrets
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, timedelta

from django import forms
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q

from appointments.forms import AppointmentForm
from appointments.models import Appointment, AppointmentType
from appointments.services import ScheduleConflict, conflicts, save_appointment
from customers.forms import CUSTOMER_FIELDS, CustomerForm
from customers.models import Customer
from customers.services import create_customer, update_customer
from extensions.forms import POSITION_FIELDS, PositionForm
from extensions.models import ExtensionPosition
from extensions.services import create_position

from .models import ImportReceipt
from .parser import ImportProblem, canonical, parse

LOCK = threading.RLock()
DRAFTS = {}
TTL = 30 * 60


@dataclass
class Draft:
    owner: int
    session: str
    payload: dict
    source_digest: str
    created: float = field(default_factory=time.monotonic)
    key: uuid.UUID = field(default_factory=uuid.uuid4)
    plan: dict | None = None
    confirmation: str = ""
    edited: object = None
    receipt_id: object = None
    lock: object = field(default_factory=threading.RLock)


def prepare(user, session, text):
    payload, digest = parse(text)
    receipt = ImportReceipt.objects.filter(owner=user, import_id=payload["id"]).first()
    if receipt:
        if receipt.source_digest != digest:
            raise ImportProblem(
                "Diese Importkennung wurde bereits mit anderem Inhalt verwendet. Bitte eine neue Kennung erstellen lassen."
            )
        return None, receipt
    with LOCK:
        for key in list(DRAFTS):
            if time.monotonic() - DRAFTS[key].created > TTL:
                del DRAFTS[key]
        owned = [draft for draft in DRAFTS.values() if draft.owner == user.pk]
        for old in sorted(owned, key=lambda draft: draft.created)[:-2]:
            DRAFTS.pop(old.key, None)
        draft = Draft(user.pk, session, payload, digest)
        DRAFTS[draft.key] = draft
        timer = threading.Timer(TTL, expire, args=[draft.key])
        timer.daemon = True
        timer.start()
    return draft, None


def expire(key):
    with LOCK:
        draft = DRAFTS.get(key)
    if draft is None:
        return
    with draft.lock, LOCK:
        if time.monotonic() - draft.created >= TTL:
            DRAFTS.pop(draft.key, None)
            draft.payload, draft.plan, draft.edited = {}, None, None


def find(key, user, session):
    with LOCK:
        draft = DRAFTS.get(key)
        if (
            not draft
            or draft.owner != user.pk
            or draft.session != session
            or time.monotonic() - draft.created > TTL
        ):
            raise ImportProblem(
                "Diese Vorschau ist abgelaufen oder gehört zu einer anderen Anmeldung. Bitte den Text erneut teilen oder einfügen."
            )
        return draft


class CustomerChoice(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj} · {obj.phone or obj.email} · Akte {obj.pk.hex[:8]}"


class TargetForm(forms.Form):
    target = CustomerChoice(
        label="Vorhandene Kundin auswählen", queryset=Customer.objects.none(), required=False
    )
    same_name = forms.BooleanField(
        label="Trotz des angezeigten Ähnlichkeitshinweises eine neue, andere Kundin anlegen",
        required=False,
    )
    apply = forms.BooleanField(
        label="Die angezeigten Änderungen an der ausgewählten Kundenakte übernehmen", required=False
    )

    def __init__(self, *args, user, mode, patch, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["target"].queryset = Customer.objects.for_user(user)
        self.fields["target"].required = mode == "existing"
        self.fields["apply"].required = mode == "existing" and bool(patch)


class IntakeAppointmentForm(AppointmentForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop("customer")


def duplicate_extension(customer, data):
    return ExtensionPosition.objects.filter(
        customer=customer, **{key: data[key] for key in POSITION_FIELDS if key != "notes"}
    ).exists()


def duplicate_appointment(customer, data):
    return Appointment.objects.filter(
        owner=customer.owner, customer=customer, start_at=data["start_at"], end_at=data["end_at"]
    ).exists()


def review(draft, user, posted=None):
    draft.plan, draft.confirmation = None, ""
    if posted is not None:
        draft.edited = posted.copy()
    else:
        posted = draft.edited
    customers, positions, appointments, problems = [], [], [], []
    plan = {"customers": [], "extensions": [], "appointments": []}
    selected = {}
    new_customers = set()
    for index, incoming in enumerate(draft.payload["customers"]):
        prefix = f"c{index}"
        target = (
            TargetForm(
                posted, prefix=prefix, user=user, mode=incoming["mode"], patch=incoming["data"]
            )
            if posted is not None
            else TargetForm(
                {}, prefix=prefix, user=user, mode=incoming["mode"], patch=incoming["data"]
            )
        )
        target_valid = target.is_valid()
        existing = target.cleaned_data.get("target")
        data = incoming["data"]
        fields = list(CUSTOMER_FIELDS) if incoming["mode"] == "new" else list(data)
        if incoming["mode"] == "existing":
            patch_form = forms.Form(
                posted
                if posted is not None
                else {f"{prefix}-field-{key}": value for key, value in data.items()},
                prefix=prefix + "-field",
            )
            for name in fields:
                patch_form.fields[name] = copy.deepcopy(CustomerForm.base_fields[name])
            patch_valid = patch_form.is_valid()
            if existing and patch_valid:
                full = {
                    name: getattr(existing, name) if getattr(existing, name) is not None else ""
                    for name in CUSTOMER_FIELDS
                }
                full.update(patch_form.cleaned_data)
                full["version"] = existing.version
                form = CustomerForm(full, instance=existing)
                valid = form.is_valid()
                for key, errors in form.errors.items():
                    for error in errors:
                        patch_form.add_error(key if key in patch_form.fields else None, error)
                cleaned = form.cleaned_data if valid else None
            else:
                valid, cleaned = patch_valid and bool(existing), None
            display_form = patch_form
        else:
            form_data = (
                posted
                if posted is not None
                else {f"{prefix}-field-{key}": value for key, value in data.items()}
            )
            display_form = CustomerForm(form_data, prefix=prefix + "-field")
            valid = True if existing else display_form.is_valid()
            cleaned = None if existing else display_form.cleaned_data
        matches = []
        customer_signature = None
        if valid and not existing:
            first = cleaned.get("first_name", "").casefold()
            last = cleaned.get("last_name", "").casefold()
            phone = "".join(c for c in cleaned.get("phone", "") if c.isdigit())
            email = cleaned.get("email", "").casefold()
            customer_signature = {"name:" + canonical([first, last])}
            if phone:
                customer_signature.add("phone:" + phone)
            if email:
                customer_signature.add("email:" + email)
            if customer_signature & new_customers:
                display_form.add_error(
                    None,
                    "Diese neue Kundin kommt im Import doppelt vor. Bitte nur eine Kundenreferenz verwenden.",
                )
                valid = False
            new_customers.update(customer_signature)
            matches = [
                person
                for person in Customer.objects.for_user(user).only(
                    "first_name", "last_name", "phone_digits", "email"
                )
                if (
                    (person.first_name.casefold() == first and person.last_name.casefold() == last)
                    or (phone and person.phone_digits == phone)
                    or (email and person.email.casefold() == email)
                )
            ]
            if matches and not target.cleaned_data.get("same_name"):
                target.add_error(
                    None,
                    "Ähnliche Kundendaten sind bereits vorhanden. Bitte eine vorhandene Kundin auswählen oder ausdrücklich eine andere neue Kundin bestätigen.",
                )
                target_valid = False
        valid = valid and target_valid
        if not valid:
            problems.append("Bitte die Kundenzuordnung und markierten Kundenfelder prüfen.")
        entry = {
            "ref": incoming["ref"],
            "mode": "existing" if existing else incoming["mode"],
            "existing": existing,
            "version": existing.version if existing else None,
            "data": cleaned,
            "patch": bool(data) and incoming["mode"] == "existing",
            "known_matches": [str(person.pk) for person in matches],
        }
        if existing:
            selected[incoming["ref"]] = existing
        customers.append(
            {
                "incoming": incoming,
                "target": target,
                "form": display_form,
                "existing": existing,
                "matches": matches,
                "entry": entry,
            }
        )
        plan["customers"].append(entry)
    for name, incoming_list in [
        ("extensions", draft.payload["extensions"]),
        ("appointments", draft.payload["appointments"]),
    ]:
        seen = set()
        for index, incoming in enumerate(incoming_list):
            prefix = ("x" if name == "extensions" else "a") + str(index)
            initial = dict(incoming["data"])
            if name == "appointments":
                candidates = list(
                    AppointmentType.objects.filter(Q(owner=user) | Q(owner__isnull=True))
                )
                names = [
                    kind
                    for kind in candidates
                    if kind.name.casefold() == str(initial.get("appointment_type", "")).casefold()
                ]
                initial["appointment_type"] = names[0].pk if len(names) == 1 else ""
                initial.setdefault("buffer_minutes", "0")
                initial.setdefault("status", "planned")
            bound = (
                posted
                if posted is not None
                else {f"{prefix}-{key}": value for key, value in initial.items()}
            )
            form = (
                PositionForm(bound, prefix=prefix)
                if name == "extensions"
                else IntakeAppointmentForm(bound, prefix=prefix, user=user)
            )
            valid = form.is_valid()
            if valid:
                clean = dict(form.cleaned_data)
                clean.pop("allow_overlap", None)
                customer = selected.get(incoming["customer_ref"])
                if customer and (
                    duplicate_extension(customer, clean)
                    if name == "extensions"
                    else duplicate_appointment(customer, clean)
                ):
                    form.add_error(
                        None,
                        "Ein identischer Eintrag ist für diese Kundin bereits vorhanden. Es wird keine Kopie angelegt.",
                    )
                    valid = False
                if name == "appointments":
                    overlap = conflicts(
                        user=user,
                        start=clean["start_at"],
                        end=clean["end_at"],
                        buffer=clean["buffer_minutes"],
                    )
                    if overlap:
                        form.add_error(
                            None,
                            "Dieser Termin überschneidet sich mit einer vorhandenen Belegung. Bitte die Zeiten ändern; im Import wird kein Konflikt automatisch übernommen.",
                        )
                        valid = False
                signature = canonical(
                    [
                        str(customer.pk) if customer else incoming["customer_ref"],
                        {
                            key: value
                            for key, value in clean.items()
                            if key not in ["notes", "version"]
                        },
                    ]
                )
                if signature in seen:
                    form.add_error(None, "Dieser Eintrag kommt im Import doppelt vor.")
                    valid = False
                seen.add(signature)
                if valid:
                    plan[name].append({"ref": incoming["customer_ref"], "data": clean})
            if not valid:
                problems.append("Bitte die markierten Positionen und Termine prüfen.")
            (positions if name == "extensions" else appointments).append(
                {"ref": incoming["customer_ref"], "form": form}
            )
    # Auch neue Termine untereinander dürfen sich nicht unbemerkt überschneiden.
    for index, item in enumerate(plan["appointments"]):
        a = item["data"]
        for other in plan["appointments"][:index]:
            b = other["data"]
            if a["start_at"].astimezone(UTC) < b["end_at"].astimezone(UTC) + timedelta(
                minutes=b["buffer_minutes"]
            ) and b["start_at"].astimezone(UTC) < a["end_at"].astimezone(UTC) + timedelta(
                minutes=a["buffer_minutes"]
            ):
                problems.append(
                    "Zwei Termine im Import überschneiden sich. Bitte die Uhrzeiten prüfen."
                )
    if not problems and posted is not None:
        digest = hashlib.sha256(canonical(plan).encode()).hexdigest()
        if ImportReceipt.objects.filter(owner=user, plan_digest=digest).exists():
            problems.append("Diese vollständig identischen Daten wurden bereits übernommen.")
        else:
            draft.plan, draft.confirmation = plan, secrets.token_urlsafe(32)
            draft.plan["digest"] = digest
    return {
        "customers": customers,
        "positions": positions,
        "appointments": appointments,
        "problems": list(dict.fromkeys(problems)),
        "ready": draft.plan is not None,
    }


@transaction.atomic
def commit(draft, user, confirmation):
    if draft.receipt_id and secrets.compare_digest(confirmation, draft.confirmation):
        return ImportReceipt.objects.get(owner=user, pk=draft.receipt_id)
    if not draft.plan or not secrets.compare_digest(confirmation, draft.confirmation):
        raise ImportProblem("Bitte die aktuelle Vorschau zuerst prüfen.")
    get_user_model().objects.select_for_update().get(pk=user.pk)
    prior = (
        ImportReceipt.objects.filter(owner=user)
        .filter(Q(import_id=draft.payload["id"]) | Q(plan_digest=draft.plan["digest"]))
        .first()
    )
    if prior:
        return prior
    resolved = {}
    counts = {"customers": 0, "updates": 0, "extensions": 0, "appointments": 0}
    for incoming in draft.plan["customers"]:
        if incoming["existing"]:
            person = (
                Customer.objects.for_user(user).select_for_update().get(pk=incoming["existing"].pk)
            )
            if person.version != incoming["version"]:
                raise ImportProblem(
                    "Eine gewählte Kundenakte wurde inzwischen geändert. Bitte die Vorschau neu prüfen."
                )
            if incoming["patch"]:
                person = update_customer(
                    customer_id=person.pk, user=user, cleaned_data=incoming["data"]
                )
                counts["updates"] += 1
        else:
            data = incoming["data"]
            first, last = data["first_name"].casefold(), data["last_name"].casefold()
            phone = "".join(c for c in data["phone"] if c.isdigit())
            email = data["email"].casefold()
            for candidate in Customer.objects.for_user(user):
                matches = (
                    (
                        candidate.first_name.casefold() == first
                        and candidate.last_name.casefold() == last
                    )
                    or (phone and candidate.phone_digits == phone)
                    or (email and candidate.email.casefold() == email)
                )
                if matches and str(candidate.pk) not in incoming["known_matches"]:
                    raise ImportProblem(
                        "Ähnliche Kundendaten wurden inzwischen angelegt. Bitte die Vorschau neu prüfen."
                    )
            person = create_customer(user=user, cleaned_data=data)
            counts["customers"] += 1
        resolved[incoming["ref"]] = person
    for incoming in draft.plan["extensions"]:
        person = resolved[incoming["ref"]]
        if duplicate_extension(person, incoming["data"]):
            raise ImportProblem(
                "Eine Extensions-Position wurde inzwischen bereits angelegt. Bitte neu prüfen."
            )
        create_position(customer_id=person.pk, user=user, cleaned_data=incoming["data"])
        counts["extensions"] += 1
    for incoming in draft.plan["appointments"]:
        person = resolved[incoming["ref"]]
        if duplicate_appointment(person, incoming["data"]):
            raise ImportProblem("Dieser Termin besteht inzwischen bereits. Bitte neu prüfen.")
        try:
            save_appointment(
                user=user, data=incoming["data"] | {"customer": person, "allow_overlap": False}
            )
        except ScheduleConflict:
            raise ImportProblem(
                "Eine Terminzeit wurde inzwischen belegt. Es wurde nichts aus diesem Paket gespeichert."
            ) from None
        counts["appointments"] += 1
    receipt = ImportReceipt.objects.create(
        owner=user,
        import_id=draft.payload["id"],
        source_digest=draft.source_digest,
        plan_digest=draft.plan["digest"],
        counts=counts,
    )

    # Erst nach erfolgreichem äußerem Commit den personenbezogenen Entwurf verwerfen.
    def clear():
        draft.receipt_id = receipt.pk
        draft.payload = {"id": str(receipt.import_id)}
        draft.edited, draft.plan = None, None

    transaction.on_commit(clear)
    return receipt
