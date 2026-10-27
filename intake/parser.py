"""Explizites Datenformat, keine KI-Ausführung und kein Abruf von Teilen-Links."""

import hashlib
import json
import re
import uuid
from decimal import Decimal

from customers.forms import CUSTOMER_FIELDS
from extensions.forms import POSITION_FIELDS

MAX_BYTES = 65536
APPOINTMENT_FIELDS = {
    "appointment_type",
    "day",
    "begin",
    "finish",
    "end_day",
    "buffer_minutes",
    "status",
    "notes",
}


class ImportProblem(Exception):
    pass


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ImportProblem(
                "Ein JSON-Feld kommt doppelt vor. Bitte die Antwort neu erstellen lassen."
            )
        result[key] = value
    return result


def bad_constant(value):
    raise ImportProblem("NaN und unendliche Zahlen sind im Import nicht erlaubt.")


def shape(data, allowed, required=()):
    if not isinstance(data, dict) or set(data) - set(allowed) or not set(required).issubset(data):
        raise ImportProblem(
            "Das Importformat enthält fehlende oder unbekannte Felder. Bitte die Formatvorlage verwenden."
        )


def scalars(data):
    if any(
        not isinstance(value, (str, int, Decimal, type(None))) or isinstance(value, bool)
        for value in data.values()
    ):
        raise ImportProblem("Datenfelder dürfen nur Text, Zahlen oder null enthalten.")
    return {name: "" if value is None else str(value) for name, value in data.items()}


def canonical(value):
    def default(item):
        if hasattr(item, "pk"):
            return str(item.pk)
        if isinstance(item, Decimal):
            return format(item.normalize(), "f")
        if hasattr(item, "isoformat"):
            return item.isoformat()
        return str(item)

    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=default
    )


def parse(text):
    if not isinstance(text, str) or len(text.encode("utf-8")) > MAX_BYTES:
        raise ImportProblem(
            "Der Import darf höchstens 64 KiB Text enthalten. Bitte kleinere Pakete teilen."
        )
    text = text.strip()
    if re.fullmatch(r"https?://\S+", text):
        raise ImportProblem(
            "Geteilt wurde nur ein Link. Haarvinci ruft diesen Link nicht ab. Bitte in ChatGPT den vollständigen Antworttext kopieren und „Aus ChatGPT einfügen“ wählen."
        )
    fences = re.findall(r"```(?:json|haarvinci-import)?\s*\n([\s\S]*?)```", text, flags=re.I)
    if fences:
        if len(fences) != 1:
            raise ImportProblem("Bitte genau ein Importpaket mit einem JSON-Block teilen.")
        text = fences[0].strip()
    try:
        data = json.loads(
            text, object_pairs_hook=unique_pairs, parse_float=Decimal, parse_constant=bad_constant
        )
    except (ValueError, RecursionError):
        raise ImportProblem(
            "Der Text ist kein gültiges Haarvinci-JSON. Bitte die gekennzeichnete Importantwort vollständig kopieren."
        ) from None
    shape(
        data,
        {"format", "version", "id", "customers", "extensions", "appointments"},
        ["format", "version", "id", "customers"],
    )
    if (
        data["format"] != "haarvinci.import"
        or type(data["version"]) is not int
        or data["version"] != 1
    ):
        raise ImportProblem(
            "Dieses Format wird nicht unterstützt. Erwartet wird haarvinci.import, Version 1."
        )
    try:
        data["id"] = str(uuid.UUID(data["id"]))
    except (ValueError, TypeError, AttributeError):
        raise ImportProblem("Die Importkennung muss eine gültige UUID sein.") from None
    refs = set()
    for key, limit in [("customers", 10), ("extensions", 25), ("appointments", 25)]:
        data.setdefault(key, [])
        if not isinstance(data[key], list) or len(data[key]) > limit:
            raise ImportProblem(
                "Zu viele Einträge: höchstens 10 Kundinnen und jeweils 25 Extensions/Termine pro Paket."
            )
    if not data["customers"]:
        raise ImportProblem("Mindestens eine Kundenreferenz ist erforderlich.")
    for customer in data["customers"]:
        shape(customer, {"ref", "mode", "hint", "data"}, ["ref", "mode"])
        ref = customer["ref"]
        if not isinstance(ref, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", ref) or ref in refs:
            raise ImportProblem(
                "Kundenreferenzen müssen kurz, eindeutig und aus Buchstaben/Zahlen bestehen."
            )
        refs.add(ref)
        if (
            customer["mode"] not in ["new", "existing"]
            or not isinstance(customer.get("hint", ""), str)
            or len(customer.get("hint", "")) > 200
        ):
            raise ImportProblem("Kundenmodus oder Suchhinweis ist ungültig.")
        customer.setdefault("data", {})
        shape(customer["data"], CUSTOMER_FIELDS)
        customer["data"] = scalars(customer["data"])
    for name, fields in [("extensions", POSITION_FIELDS), ("appointments", APPOINTMENT_FIELDS)]:
        for item in data[name]:
            shape(item, {"customer_ref", "data"}, ["customer_ref", "data"])
            if not isinstance(item["customer_ref"], str) or item["customer_ref"] not in refs:
                raise ImportProblem("Eine Position verweist auf eine unbekannte Kundin.")
            shape(item["data"], fields)
            item["data"] = scalars(item["data"])
    digest = hashlib.sha256(canonical(data).encode()).hexdigest()
    return data, digest
