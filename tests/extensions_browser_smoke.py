"""Echte mobile Oberflächenprüfung für Haarprofile und Extensions, nur fiktive Daten."""

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

from customers.models import Customer  # noqa: E402


def assert_mobile_layout(page):
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    expect(page.get_by_role("navigation", name="Mobile Hauptnavigation")).to_be_visible()


def main():
    if not settings.DEBUG:
        raise RuntimeError("Oberflächentest nur in der lokalen Testumgebung ausführen.")
    base = os.environ.get("HAARVINCI_TEST_URL", "http://127.0.0.1:8000")
    password = secrets.token_urlsafe(25)
    user = get_user_model().objects.create_user(
        username=f"extbrowser_{uuid.uuid4().hex[:12]}", first_name="Conny", password=password
    )
    screenshots = ROOT / "test-results/extensions"
    screenshots.mkdir(parents=True, exist_ok=True)
    session_keys = []
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
            page.goto(base + "/kundinnen/neu/")
            for name, value in {
                "first_name": "Mila",
                "last_name": "Testgarten",
                "email": "mila@example.com",
                "notes": "Erfundene Kundin für den Erweiterungstest.",
            }.items():
                page.locator(f'[name="{name}"]').fill(value)
            page.locator("#haarprofil > summary").click()
            for name, value in {
                "natural_color": "Dunkelblond",
                "current_color": "Kupfer",
                "hair_structure": "Wellig",
                "natural_length": "25,5",
                "desired_length": "50",
                "hair_density": "Fein",
                "current_extensions": "Fiktive Tape-Ins",
                "hair_wishes": "Natürliche Fülle und ein sanfter Übergang.",
            }.items():
                page.locator(f'[name="{name}"]').fill(value)
            page.locator("#haarprofil").scroll_into_view_if_needed()
            assert_mobile_layout(page)
            page.screenshot(path=str(screenshots / "haarprofil-formular.png"), full_page=True)
            page.get_by_role("button", name="Kundin speichern", exact=True).click()
            expect(page.get_by_role("heading", name="Mila Testgarten", exact=True)).to_be_visible()
            detail_url = page.url
            expect(page.locator("#haarprofil")).to_contain_text("25,5 cm")
            page.get_by_role("link", name="Extensions hinzufügen", exact=True).click()
            values = {
                "manufacturer": "Fiktivhaar Atelier",
                "extension_type": "Tape-Ins",
                "color": "Naturblond",
                "color_code": "#18/22",
                "length_cm": "50,5",
                "weight_g": "100,25",
                "quantity": "4",
                "purchase_price": "-1",
                "sale_price": "249,95",
                "assigned_on": "2026-10-01",
                "notes": "Nur eine fiktive Extensions-Position.",
            }
            for name, value in values.items():
                page.locator(f'[name="{name}"]').fill(value)
            page.locator('[name="quantity_unit"]').select_option("packs")
            page.locator('[name="delivery_status"]').select_option("ordered")
            page.get_by_role("button", name="Extensions zuordnen", exact=True).click()
            expect(page.get_by_role("alert")).to_contain_text("Bitte prüfe deine Angaben.")
            expect(page.locator('[name="manufacturer"]')).to_have_value("Fiktivhaar Atelier")
            page.locator('[name="purchase_price"]').fill("149,90")
            page.screenshot(path=str(screenshots / "extensions-formular.png"), full_page=True)
            page.get_by_role("button", name="Extensions zuordnen", exact=True).click()
            expect(page.locator("[data-position]")).to_have_count(1)
            first = page.locator("[data-position]").get_attribute("data-position")
            page.locator("#extensions").scroll_into_view_if_needed()
            page.screenshot(path=str(screenshots / "extensions-kundenakte.png"), full_page=True)
            page.get_by_role("link", name="Position bearbeiten", exact=True).click()
            page.locator('[name="color"]').fill("Kupfer")
            page.locator('[name="delivery_status"]').select_option("received")
            page.get_by_role("button", name="Extensions speichern", exact=True).click()
            expect(page.locator("[data-position]")).to_contain_text("Kupfer")
            page.get_by_role("link", name="Extensions hinzufügen", exact=True).click()
            for name, value in {
                "manufacturer": "Zweites Fiktivatelier",
                "extension_type": "Bondings",
                "color": "Braun",
                "length_cm": "40",
                "weight_g": "50",
                "purchase_price": "75,20",
                "assigned_on": "2026-10-02",
            }.items():
                page.locator(f'[name="{name}"]').fill(value)
            expect(page.locator("#suggestions-manufacturer option")).to_have_attribute(
                "value", "Fiktivhaar Atelier"
            )
            page.get_by_role("button", name="Extensions zuordnen", exact=True).click()
            expect(page.locator("[data-position]")).to_have_count(2)
            second = page.locator("[data-position]").first
            expect(second).to_contain_text("Zweites Fiktivatelier")
            second.get_by_role("link", name="Position löschen", exact=True).click()
            expect(page.get_by_role("heading", name="Diese Position löschen?")).to_be_visible()
            page.get_by_role("button", name="Position endgültig löschen").click()
            expect(page.locator("[data-position]")).to_have_count(1)
            expect(page.locator("[data-position]")).to_have_attribute("data-position", first)
            page.locator("#historie > summary").click()
            page.locator("#historie").scroll_into_view_if_needed()
            expect(page.locator("#historie")).to_contain_text("Extensions gelöscht")
            expect(page.locator("#historie")).to_contain_text("Extensions geändert")
            page.screenshot(path=str(screenshots / "kundenhistorie.png"), full_page=True)
            with page.expect_download() as download_info:
                page.get_by_role("link", name="Kundenakte exportieren").click()
            data = json.loads(Path(download_info.value.path()).read_text())
            assert data["customer"]["natural_color"] == "Dunkelblond"
            assert data["extensions"][0]["purchase_price"] == "149.90"
            assert len(data["history"]) == 5
            page.get_by_role("navigation", name="Mobile Hauptnavigation").get_by_role(
                "link", name="Extensions", exact=True
            ).click()
            page.get_by_label("Kundin, Hersteller, Farbe oder Farbcode").fill("MILA")
            page.get_by_label("Lieferstatus", exact=True).select_option("received")
            page.get_by_role("button", name="Suchen", exact=True).click()
            expect(page.locator(".extension-totals")).to_contain_text("1 Position")
            expect(page.locator(".extension-totals")).to_contain_text("149,90")
            assert_mobile_layout(page)
            page.screenshot(path=str(screenshots / "extensions-uebersicht.png"), full_page=True)
            for width in [360, 390, 412, 600, 760, 1024, 1440]:
                page.set_viewport_size({"width": width, "height": 915})
                for path in [
                    "/extensions/",
                    "/kundinnen/" + detail_url.split("/kundinnen/")[1],
                    "/kundinnen/" + detail_url.split("/kundinnen/")[1] + "extensions/neu/",
                ]:
                    page.goto(base + path)
                    assert page.evaluate(
                        "document.documentElement.scrollWidth <= window.innerWidth"
                    ), f"Überlauf bei {width}px auf {path}"
            page.goto(detail_url)
            expect(page.locator("#haarprofil")).to_contain_text("Dunkelblond")
            expect(page.locator("[data-position]")).to_contain_text("Kupfer")
            session_keys.extend(
                cookie["value"] for cookie in context.cookies() if cookie["name"] == "sessionid"
            )
            assert not errors, errors
            browser.close()
        print(
            "Mobile Erweiterungen geprüft: Haarprofil, Kommawerte, Preisvalidierung, mehrere Positionen, Bearbeitung, bestätigte Löschung, Historie, Export, Eingabevorschläge, Suche/Filter und sieben Bildschirmbreiten."
        )
    finally:
        Customer.objects.filter(owner=user).delete()
        Session.objects.filter(session_key__in=session_keys).delete()
        user.delete()


if __name__ == "__main__":
    main()
