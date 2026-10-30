"""Version 2 erweitert Version 1; keine fachlichen IDs aus fremdem Text übernehmen."""

import re

TREATMENT_FIELDS = {
    "performed_on",
    "description",
    "status",
    "rows",
    "price_mode",
    "custom_price",
    "notes",
    "charge_extensions",
}
PAYMENT_FIELDS = {"amount", "booked_on", "method", "purpose", "notes", "kind"}


def validate(data, customers):
    from .parser import ImportProblem, scalars, shape

    used = set(customers)

    def identity(value):
        if (
            not isinstance(value, str)
            or not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", value)
            or value in used
        ):
            raise ImportProblem(
                "Referenzen müssen im gesamten Paket eindeutig sein (1–40 Buchstaben/Zahlen/Unterstriche/Bindestriche)."
            )
        used.add(value)

    links = {}
    for kind, prefix in [("extensions", "x"), ("appointments", "a")]:
        for index, item in enumerate(data[kind]):
            item.setdefault("ref", f"{prefix}{index + 1}")
            identity(item["ref"])
            links[item["ref"]] = (kind, item["customer_ref"])
    for kind, limit in [("treatments", 25), ("payments", 50)]:
        data.setdefault(kind, [])
        if not isinstance(data[kind], list) or len(data[kind]) > limit:
            raise ImportProblem(
                "Pro Paket sind höchstens 25 Behandlungen und 50 Geldbuchungen erlaubt."
            )
    targets = {}
    for item in data["treatments"]:
        shape(
            item,
            {
                "ref",
                "customer_ref",
                "mode",
                "hint",
                "data",
                "appointment_ref",
                "extension_refs",
                "services",
            },
            ["ref", "customer_ref", "mode"],
        )
        identity(item["ref"])
        if (
            not isinstance(item["customer_ref"], str)
            or item["customer_ref"] not in customers
            or item["mode"] not in ["new", "existing"]
        ):
            raise ImportProblem("Ungültige Kundenzuordnung oder ungültiger Behandlungsmodus.")
        item.setdefault("hint", "")
        if not isinstance(item["hint"], str) or len(item["hint"]) > 200:
            raise ImportProblem("Der Behandlungshinweis ist ungültig.")
        scalars({"hint": item["hint"]})
        item.setdefault("data", {})
        shape(item["data"], TREATMENT_FIELDS)
        if isinstance(item["data"].get("charge_extensions"), bool):
            item["data"]["charge_extensions"] = (
                "true" if item["data"]["charge_extensions"] else "false"
            )
        item["data"] = scalars(item["data"])
        if item["data"].get("charge_extensions", "") not in ["", "true", "false", "0", "1"]:
            raise ImportProblem("charge_extensions muss true oder false sein.")
        item.setdefault("extension_refs", [])
        item.setdefault("services", [])
        for field in ["extension_refs", "services"]:
            if (
                not isinstance(item[field], list)
                or len(item[field]) > 25
                or any(not isinstance(v, str) or len(v) > 120 for v in item[field])
                or len(set(item[field])) != len(item[field])
            ):
                raise ImportProblem(
                    "Extensions-Referenzen und Zusatzleistungen müssen eindeutige Textlisten sein."
                )
            scalars({str(i): v for i, v in enumerate(item[field])})
        if "appointment_ref" in item and not isinstance(item["appointment_ref"], str):
            raise ImportProblem("appointment_ref muss eine Textreferenz sein.")
        if item.get("appointment_ref"):
            ref = item["appointment_ref"]
            if not isinstance(ref, str) or links.get(ref) != ("appointments", item["customer_ref"]):
                raise ImportProblem("Die Terminreferenz muss zur selben Kundin gehören.")
        for ref in item["extension_refs"]:
            if links.get(ref) != ("extensions", item["customer_ref"]):
                raise ImportProblem("Eine Extensions-Referenz gehört nicht zur Behandlungskundin.")
        if item["mode"] == "existing" and (
            item["data"]
            or item["services"]
            or item["extension_refs"]
            or item.get("appointment_ref")
        ):
            raise ImportProblem(
                "Vorhandene Behandlungen werden im Import eindeutig ausgewählt und nur für Zahlungen verknüpft. Änderungen bitte im Behandlungsvorgang vornehmen."
            )
        targets[item["ref"]] = item
    receipts = {}
    for item in data["payments"]:
        shape(item, {"ref", "treatment_ref", "refund_of", "data"}, ["ref", "treatment_ref", "data"])
        identity(item["ref"])
        if not isinstance(item["treatment_ref"], str) or item["treatment_ref"] not in targets:
            raise ImportProblem("Eine Geldbuchung verweist auf eine unbekannte Behandlung.")
        shape(item["data"], PAYMENT_FIELDS)
        item["data"] = scalars(item["data"])
        item["data"].setdefault("kind", "receipt")
        if item["data"]["kind"] not in ["receipt", "refund"]:
            raise ImportProblem("Geldbuchungen müssen receipt oder refund sein.")
        if "refund_of" in item and not isinstance(item["refund_of"], str):
            raise ImportProblem("refund_of muss eine Textreferenz sein.")
        if item.get("refund_of"):
            ref = item["refund_of"]
            if (
                not isinstance(ref, str)
                or receipts.get(ref) != item["treatment_ref"]
                or item["data"]["kind"] != "refund"
            ):
                raise ImportProblem(
                    "Eine Erstattung muss auf einen vorhergehenden Zahlungseingang derselben Behandlung verweisen."
                )
        elif (
            item["data"]["kind"] == "refund"
            and targets[item["treatment_ref"]]["mode"] != "existing"
        ):
            raise ImportProblem(
                "Bei neuen Behandlungen benötigt eine Erstattung die refund_of-Referenz auf einen vorherigen Zahlungseingang."
            )
        if item["data"]["kind"] == "receipt":
            receipts[item["ref"]] = item["treatment_ref"]
