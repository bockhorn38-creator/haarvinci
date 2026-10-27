"""Reale Touch-Oberfläche: Importprüfung und Bestätigung mit fiktiven Daten."""

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
from django.contrib.sessions.models import Session  # noqa: E402
from playwright.sync_api import expect, sync_playwright  # noqa: E402

from appointments.models import Appointment  # noqa: E402
from customers.models import Customer  # noqa: E402
from extensions.models import ExtensionPosition  # noqa: E402
from intake.models import ImportReceipt  # noqa: E402
from tests.test_intake import bundle  # noqa: E402


def main():
    assert settings.DEBUG
    base = os.environ.get("HAARVINCI_TEST_URL", "http://127.0.0.1:8000")
    user = get_user_model().objects.create_user(
        "import_browser_" + uuid.uuid4().hex[:12], password=(password := secrets.token_urlsafe(24))
    )

    def count(model):
        from django.db import close_old_connections

        def query():
            try:
                return (
                    model.objects.filter(owner=user).count()
                    if model is ImportReceipt
                    else model.objects.for_user(user).count()
                )
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(query).result()

    screenshots = ROOT / "test-results/import"
    screenshots.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path="/usr/bin/chromium", headless=True)
            context = browser.new_context(
                viewport={"width": 412, "height": 915}, locale="de-DE", timezone_id="Europe/Berlin"
            )
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(base + "/anmelden/")
            page.get_by_label("Benutzername").fill(user.username)
            page.get_by_label("Passwort", exact=True).fill(password)
            page.get_by_role("button", name="Kundenbuch öffnen").click()
            page.goto(base + "/uebernehmen/")
            page.get_by_label("Haarvinci-Importtext").fill("https://chatgpt.com/share/fiktiv")
            page.get_by_role("button", name="Vorschau öffnen").click()
            expect(page.get_by_text("Geteilt wurde nur ein Link", exact=False).last).to_be_visible()
            payload = bundle()
            del payload["customers"][0]["data"]["last_name"]
            page.get_by_label("Haarvinci-Importtext").fill(json.dumps(payload))
            page.get_by_role("button", name="Vorschau öffnen").click()
            expect(page.get_by_role("heading", name="Deine Importvorschau.")).to_be_visible()
            expect(page.locator("#last_name-errors")).to_contain_text("erforderlich")
            assert count(Customer) == 0
            assert count(ImportReceipt) == 0
            for width in [360, 390, 412, 600, 760, 1024, 1440]:
                page.set_viewport_size({"width": width, "height": 915})
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), width
            page.set_viewport_size({"width": 412, "height": 915})
            page.screenshot(path=str(screenshots / "vorschau-pixel.png"), full_page=True)
            page.locator("#id_c0-field-last_name").fill("Fiktivblüte")
            page.get_by_role("button", name="Angaben prüfen").click()
            expect(page.get_by_role("heading", name="Diese Angaben übernehmen?")).to_be_visible()
            assert count(Customer) == 0
            page.screenshot(path=str(screenshots / "bestaetigung-pixel.png"), full_page=True)
            for width in [360, 412, 760, 1440]:
                page.set_viewport_size({"width": width, "height": 915})
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), width
            page.get_by_role("button", name="Jetzt verbindlich übernehmen").click()
            expect(page.get_by_role("heading", name="Import bereits übernommen.")).to_be_visible()
            assert count(Customer) == 1
            assert count(ExtensionPosition) == 1
            assert count(Appointment) == 1
            assert count(ImportReceipt) == 1
            receipt = page.url
            page.goto(base + "/uebernehmen/")
            page.get_by_label("Haarvinci-Importtext").fill(json.dumps(payload))
            page.get_by_role("button", name="Vorschau öffnen").click()
            expect(page).to_have_url(receipt)
            assert count(Customer) == 1
            assert not errors, errors
            browser.close()
        print(
            "Import-Oberfläche geprüft: Link-Hinweis, fehlende Pflichtfelder, Korrektur, zwei Vorschauen ohne Speicherung, atomare Bestätigung, Wiederholung ohne Duplikate und sieben Bildschirmbreiten."
        )
    finally:
        Appointment.objects.for_user(user).delete()
        Customer.objects.for_user(user).delete()
        ImportReceipt.objects.filter(owner=user).delete()
        user_id = user.pk
        user.delete()
        for session in Session.objects.all():
            if session.get_decoded().get("_auth_user_id") == str(user_id):
                session.delete()


if __name__ == "__main__":
    main()
