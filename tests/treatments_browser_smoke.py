"""Gemeinsamer Touch-Ablauf mit fiktiven Preisstaffeln, Zahlungen und Import v2."""

import json
import os
import secrets
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django  # noqa: E402

django.setup()
from django.conf import settings  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from django.db import close_old_connections  # noqa: E402
from playwright.sync_api import expect, sync_playwright  # noqa: E402

from appointments.models import Appointment  # noqa: E402
from customers.models import Customer  # noqa: E402
from intake.models import ImportReceipt  # noqa: E402
from tests.test_intake_v2 import bundle2  # noqa: E402
from treatments.models import Payment, PriceOption, Treatment  # noqa: E402


def main():
    assert settings.DEBUG
    base = os.environ.get("HAARVINCI_TEST_URL", "http://127.0.0.1:8000")
    user = get_user_model().objects.create_user(
        "salon_browser_" + uuid.uuid4().hex[:12],
        first_name="Conny",
        password=(password := secrets.token_urlsafe(24)),
    )
    PriceOption.objects.create(
        owner=user, name="Fiktive zwei Reihen", category="weaving", rows=2, price="145.00"
    )
    PriceOption.objects.create(
        owner=user, name="Fiktive Haarwäsche", category="service", price="20.00"
    )
    person = Customer.objects.create(
        owner=user, first_name="Nele", last_name="Salonfiktiv", email="nele@example.com"
    )
    screenshots = ROOT / "test-results/treatments"
    screenshots.mkdir(parents=True, exist_ok=True)

    def query(fn):
        def run():
            try:
                return fn()
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(run).result()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path="/usr/bin/chromium", headless=True)
            context = browser.new_context(
                viewport={"width": 412, "height": 915}, locale="de-DE", timezone_id="Europe/Berlin"
            )
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on(
                "response",
                lambda response: (
                    errors.append(f"HTTP {response.status}") if response.status >= 500 else None
                ),
            )
            page.goto(base + "/anmelden/")
            page.get_by_label("Benutzername").fill(user.username)
            page.get_by_label("Passwort", exact=True).fill(password)
            page.get_by_role("button", name="Kundenbuch öffnen").click()
            page.goto(base + "/behandlungen/neu/?kundin=" + str(person.pk))
            page.get_by_label("Weaving-Reihen", exact=False).fill("2")
            page.get_by_label("Fiktive Haarwäsche", exact=False).check()
            page.get_by_role("button", name="Preis prüfen", exact=True).click()
            expect(page.get_by_role("heading", name="Deine Preisübersicht")).to_be_visible()
            expect(page.locator(".money-total")).to_have_text("165,00 €")
            assert query(lambda: Treatment.objects.for_user(user).count()) == 0
            for width in [360, 390, 412, 600, 760, 1024, 1440]:
                page.set_viewport_size({"width": width, "height": 915})
                assert page.evaluate("document.documentElement.scrollWidth<=innerWidth"), width
            page.set_viewport_size({"width": 412, "height": 915})
            page.screenshot(path=str(screenshots / "preisvorschau-pixel.png"), full_page=True)
            page.get_by_role("button", name="Behandlung speichern", exact=True).click()
            expect(
                page.get_by_role("heading", name="Vereinbarter Preis", exact=True)
            ).to_be_visible()
            detail = page.url
            page.get_by_role("link", name="Zahlung dokumentieren", exact=True).click()
            page.get_by_label("Betrag (€)", exact=True).fill("50,00")
            page.get_by_role("button", name="Zahlung verbindlich buchen").click()
            expect(page).to_have_url(detail)
            expect(page.locator(".salon-balances")).to_contain_text("115,00 €")
            page.get_by_role("link", name="Bearbeiten", exact=True).click()
            page.get_by_label("Status", exact=True).select_option("completed")
            page.get_by_label("Behandlungsdokumentation", exact=False).fill(
                "Fiktive Behandlung vollständig dokumentiert."
            )
            page.get_by_role("button", name="Preis prüfen", exact=True).click()
            page.get_by_role("button", name="Behandlung speichern", exact=True).click()
            expect(page).to_have_url(detail)
            page.get_by_role("link", name="Zahlung dokumentieren", exact=True).click()
            page.get_by_label("Betrag (€)", exact=True).fill("115,00")
            page.get_by_label("Buchungsart", exact=True).select_option("final")
            page.get_by_role("button", name="Zahlung verbindlich buchen").click()
            expect(page.locator(".salon-balances")).to_contain_text("0,00 €")
            page.screenshot(path=str(screenshots / "behandlung-bezahlt-pixel.png"), full_page=True)
            page.get_by_role("link", name="Behandlung stornieren", exact=True).click()
            page.get_by_label("Grund", exact=True).fill("Fiktiver Stornofall")
            page.get_by_role("button", name="Stornierung bestätigen").click()
            expect(page.get_by_text("Noch zu erstatten:", exact=False)).to_be_visible()
            for i in range(2):
                page.get_by_role("link", name="Rückerstattung dokumentieren", exact=True).click()
                page.get_by_label("Notiz / Erstattungsgrund", exact=True).fill(
                    f"Fiktive Geldrückgabe {i + 1}"
                )
                page.get_by_role("button", name="Erstattung verbindlich buchen").click()
                expect(page).to_have_url(detail)
            assert query(lambda: Treatment.objects.for_user(user).get().net_paid) == 0
            page.goto(base + "/behandlungen/statistik/")
            expect(page.get_by_role("heading", name="Deine Statistik.")).to_be_visible()
            expect(page.get_by_text("Keine offenen Forderungen.", exact=True)).to_be_visible()
            for width in [360, 412, 760, 1440]:
                page.set_viewport_size({"width": width, "height": 915})
                assert page.evaluate("document.documentElement.scrollWidth<=innerWidth"), width
            page.set_viewport_size({"width": 412, "height": 915})
            page.screenshot(path=str(screenshots / "finanzstatistik-pixel.png"), full_page=True)
            payload = bundle2()
            page.goto(base + "/uebernehmen/")
            page.get_by_label("Haarvinci-Importtext").fill(json.dumps(payload))
            page.get_by_role("button", name="Vorschau öffnen").click()
            expect(page.get_by_role("heading", name="Behandlung · b1", exact=True)).to_be_visible()
            page.get_by_role("button", name="Angaben prüfen", exact=True).click()
            expect(page.get_by_role("heading", name="Diese Angaben übernehmen?")).to_be_visible()
            assert query(lambda: Treatment.objects.for_user(user).count()) == 1
            page.screenshot(
                path=str(screenshots / "import2-bestaetigung-pixel.png"), full_page=True
            )
            for width in [360, 412, 760, 1440]:
                page.set_viewport_size({"width": width, "height": 915})
                assert page.evaluate("document.documentElement.scrollWidth<=innerWidth"), width
            page.get_by_role("button", name="Jetzt verbindlich übernehmen").click()
            expect(page.get_by_role("heading", name="Import bereits übernommen.")).to_be_visible()
            assert query(lambda: Treatment.objects.for_user(user).count()) == 2
            assert query(lambda: Payment.objects.for_user(user).count()) == 6
            assert not errors, errors
            browser.close()
        print(
            "Touch-Gesamtablauf bestanden: Preise, Zusatzleistungen, Anzahlung, Durchführung, Restzahlung, Storno, mehrere Erstattungen, Statistik und verknüpfter Import v2; sieben Bildschirmbreiten."
        )
    finally:
        Payment.objects.for_user(user).filter(kind="refund").delete()
        Payment.objects.for_user(user).delete()
        Treatment.objects.for_user(user).delete()
        Appointment.objects.for_user(user).delete()
        Customer.objects.for_user(user).delete()
        PriceOption.objects.for_user(user).delete()
        ImportReceipt.objects.filter(owner=user).delete()
        user.delete()


if __name__ == "__main__":
    main()
