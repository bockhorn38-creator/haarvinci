"""Echte Chromium-Prüfung: Anmelden, mobile Kundenverwaltung, Export und Abmelden.

Start vorher: bash scripts/start.sh
Aufruf: uv run python tests/browser_smoke.py
Es werden ein temporärer Zugang und fiktive Kundinnen angelegt und wieder entfernt.
"""

import json
import os
import secrets
import sys
import uuid
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

from customers.management.commands.init_demo import DEMO  # noqa: E402
from customers.models import Customer  # noqa: E402


def assert_mobile_layout(page):
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), (
        "Seite läuft horizontal über"
    )
    expect(page.get_by_role("navigation", name="Mobile Hauptnavigation")).to_be_visible()


def main():
    if not settings.DEBUG:
        raise RuntimeError("Browser-Test nur in der lokalen Testumgebung ausführen.")
    base = os.environ.get("HAARVINCI_TEST_URL", "http://127.0.0.1:8000")
    screenshots = ROOT / "test-results"
    screenshots.mkdir(exist_ok=True)
    password = secrets.token_urlsafe(25)
    user = get_user_model().objects.create_user(
        username=f"browser_{uuid.uuid4().hex[:12]}", first_name="Conny", password=password
    )
    for first, last, phone, email, consultation, notes in DEMO:
        Customer.objects.create(
            owner=user,
            first_name=first,
            last_name=last,
            phone=phone,
            email=email,
            first_consultation=consultation,
            notes=notes,
        )
    session_keys = []
    try:
        with sync_playwright() as p:
            chromium = os.getenv("CHROMIUM_PATH", "/usr/bin/chromium")
            browser = p.chromium.launch(
                executable_path=chromium if Path(chromium).exists() else None, headless=True
            )
            context = browser.new_context(
                viewport={"width": 1440, "height": 1050},
                locale="de-DE",
                timezone_id="Europe/Berlin",
                device_scale_factor=1,
            )
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on(
                "response",
                lambda response: (
                    errors.append(f"HTTP {response.status}: {response.url}")
                    if response.status >= 500
                    else None
                ),
            )
            page.goto(base + "/")
            expect(page.get_by_label("Benutzername")).to_be_visible()
            page.screenshot(path=str(screenshots / "anmeldung-desktop.png"), full_page=True)
            page.get_by_label("Benutzername").fill(user.username)
            page.get_by_label("Passwort", exact=True).fill(password)
            page.get_by_role("button", name="Kundenbuch öffnen").click()
            expect(
                page.get_by_role("heading", name="Schön, dass du da bist, Conny.")
            ).to_be_visible()
            page.screenshot(path=str(screenshots / "uebersicht-desktop.png"), full_page=True)
            page.set_viewport_size({"width": 412, "height": 915})
            assert_mobile_layout(page)
            page.screenshot(path=str(screenshots / "uebersicht-pixel.png"), full_page=True)
            page.get_by_role("navigation", name="Mobile Hauptnavigation").get_by_role(
                "link", name="Kundinnen"
            ).click()
            expect(page.get_by_role("heading", name="Deine Kundinnen.")).to_be_visible()
            page.get_by_role("searchbox").fill("marie sommer")
            page.get_by_role("button", name="Suchen", exact=True).click()
            expect(page.get_by_role("heading", name="Marie Sommer")).to_be_visible()
            expect(page.get_by_role("heading", name="Lena Bergmann")).to_have_count(0)
            page.get_by_role("link", name="Suche zurücksetzen").click()
            page.screenshot(path=str(screenshots / "kundinnen-pixel.png"), full_page=True)
            page.get_by_role("link", name="Neue Kundin", exact=True).click()
            page.get_by_label("Vorname", exact=True).fill("Mila")
            page.get_by_label("Nachname", exact=True).fill("Testgarten")
            page.get_by_role("button", name="Kundin speichern", exact=True).click()
            expect(page.get_by_role("heading", name="Bitte prüfe deine Angaben.")).to_be_visible()
            expect(page.get_by_label("Vorname", exact=True)).to_have_value("Mila")
            page.get_by_label("Telefonnummer", exact=False).fill("+49 151 0000 0199")
            page.get_by_label("E-Mail-Adresse", exact=False).fill("mila.testgarten@example.com")
            page.get_by_label("Geburtsdatum", exact=False).fill("1992-03-14")
            page.get_by_label("Erste Beratung", exact=False).fill("2026-10-01")
            page.get_by_label("Persönliche Notizen", exact=False).fill(
                "Fiktive Browser-Testkundin. Natürliche Fülle gewünscht."
            )
            assert_mobile_layout(page)
            page.screenshot(path=str(screenshots / "neue-kundin-pixel.png"), full_page=True)
            page.get_by_role("button", name="Kundin speichern", exact=True).click()
            expect(page.get_by_role("heading", name="Mila Testgarten")).to_be_visible()
            detail_url = page.url
            page.reload()
            expect(page.get_by_text("Natürliche Fülle gewünscht.", exact=False)).to_be_visible()
            page.get_by_role("link", name="Bearbeiten", exact=True).click()
            page.get_by_label("Persönliche Notizen", exact=False).fill(
                "Fiktive Notiz nach Bearbeitung. Dauerhaft gespeichert."
            )
            page.get_by_role("button", name="Änderungen speichern", exact=True).click()
            expect(page.get_by_text("Dauerhaft gespeichert.", exact=False)).to_be_visible()
            page.screenshot(path=str(screenshots / "kundenakte-pixel.png"), full_page=True)
            with page.expect_download() as download_info:
                page.get_by_role("link", name="Kundenakte exportieren").click()
            download = download_info.value
            data = json.loads(Path(download.path()).read_text())
            assert data["customer"]["last_name"] == "Testgarten"
            assert data["customer"]["notes"].endswith("Dauerhaft gespeichert.")
            for width in [360, 390, 412, 600, 760, 1024, 1440]:
                page.set_viewport_size({"width": width, "height": 915})
                page.goto(base + "/kundinnen/neu/")
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), (
                    f"Formular läuft bei {width}px über"
                )
            page.set_viewport_size({"width": 412, "height": 915})
            page.get_by_role("navigation", name="Mobile Hauptnavigation").get_by_role(
                "link", name="Konto", exact=True
            ).click()
            expect(page.get_by_role("link", name="Passwort ändern")).to_be_visible()
            session_keys.extend(
                cookie["value"] for cookie in context.cookies() if cookie["name"] == "sessionid"
            )
            page.get_by_role("button", name="Sicher abmelden").click()
            page.goto(detail_url)
            expect(page.get_by_label("Benutzername")).to_be_visible()
            assert_mobile = page.evaluate(
                "document.documentElement.scrollWidth <= window.innerWidth"
            )
            assert assert_mobile
            page.screenshot(path=str(screenshots / "anmeldung-pixel.png"), full_page=True)
            manifest = context.request.get(base + "/manifest.webmanifest").json()
            assert manifest["display"] == "standalone"
            for icon in manifest["icons"]:
                assert context.request.get(base + icon["src"]).status == 200
            assert context.request.get(base + "/sw.js").status == 200
            assert not errors, errors
            browser.close()
        print(
            "Browser-Test bestanden: Anmeldung, Suche, Validierung, Anlegen, Neuladen, Bearbeiten, Export, Abmelden, App-Dateien und 7 Bildschirmbreiten."
        )
        print("Bildschirmfotos: test-results/ (ausschließlich fiktive Daten).")
    finally:
        Customer.objects.filter(owner=user).delete()
        Session.objects.filter(session_key__in=session_keys).delete()
        user.delete()


if __name__ == "__main__":
    main()
