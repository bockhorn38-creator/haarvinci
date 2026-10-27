"""Echte Touch-Oberfläche für den lokalen Kalender; ausschließlich fiktive Daten."""

import os
import secrets
import sys
import uuid
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django  # noqa: E402

django.setup()
from django.conf import settings  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from django.contrib.sessions.models import Session  # noqa: E402
from django.utils import timezone  # noqa: E402
from playwright.sync_api import expect, sync_playwright  # noqa: E402

from appointments.models import Appointment, AppointmentType, CalendarSettings  # noqa: E402
from customers.models import Customer  # noqa: E402


def main():
    if not settings.DEBUG:
        raise RuntimeError("Nur in der lokalen Testumgebung ausführen.")
    base = os.environ.get("HAARVINCI_TEST_URL", "http://127.0.0.1:8000")
    user = get_user_model().objects.create_user(
        username="calendar_" + uuid.uuid4().hex[:12],
        first_name="Conny",
        password=(password := secrets.token_urlsafe(24)),
    )
    customer = Customer.objects.create(
        owner=user, first_name="Mila", last_name="Testgarten", email="mila@example.com"
    )
    kind = AppointmentType.objects.filter(owner__isnull=True).first()
    tomorrow, past = (
        str(timezone.localdate() + timedelta(days=1)),
        str(timezone.localdate() - timedelta(days=2)),
    )
    screenshots = ROOT / "test-results/calendar"
    screenshots.mkdir(parents=True, exist_ok=True)
    sessions = []
    try:
        with sync_playwright() as p:
            chromium = os.getenv("CHROMIUM_PATH", "/usr/bin/chromium")
            browser = p.chromium.launch(
                executable_path=chromium if Path(chromium).exists() else None, headless=True
            )
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
            expect(
                page.get_by_role("heading", name="Schön, dass du da bist, Conny.")
            ).to_be_visible()
            page.get_by_role("navigation", name="Mobile Hauptnavigation").get_by_role(
                "link", name="Kalender", exact=True
            ).click()
            expect(page.get_by_role("heading", name="Dein Kalender.")).to_be_visible()
            page.get_by_role("link", name="Neuer Termin", exact=True).click()

            def fill(day, begin, finish, status="planned"):
                page.locator("[name=customer]").select_option(str(customer.pk))
                page.locator("[name=appointment_type]").select_option(str(kind.pk))
                for name, value in {
                    "day": day,
                    "begin": begin,
                    "finish": finish,
                    "buffer_minutes": "15",
                    "notes": "Fiktiver Kalender-Testtermin.",
                }.items():
                    page.locator(f"[name={name}]").fill(value)
                page.locator("[name=status]").select_option(status)

            fill(tomorrow, "10:00", "11:00", "confirmed")
            expect(page.locator("#duration-preview")).to_have_text("60 Minuten")
            page.screenshot(path=str(screenshots / "termin-formular-pixel.png"), full_page=True)
            page.get_by_role("button", name="Termin speichern", exact=True).click()
            expect(page.get_by_role("link", name="Bearbeiten / verschieben")).to_be_visible()
            appointment = page.url
            page.get_by_role("link", name="Bearbeiten / verschieben").click()
            page.locator("[name=begin]").fill("12:00")
            page.locator("[name=finish]").fill("13:30")
            expect(page.locator("#duration-preview")).to_have_text("90 Minuten")
            page.get_by_role("button", name="Termin speichern", exact=True).click()
            expect(page.get_by_text("90 Minuten", exact=True)).to_be_visible()
            page.goto(base + "/kalender/neu/")
            fill(tomorrow, "13:30", "14:30")
            page.get_by_role("button", name="Termin speichern", exact=True).click()
            expect(page.locator(".overlap-warning")).to_contain_text("Zeit ist bereits belegt")
            page.get_by_label("Die angezeigte Überschneidung bewusst übernehmen").check()
            page.get_by_role("button", name="Termin speichern", exact=True).click()
            page.get_by_role("link", name="Termin absagen", exact=True).click()
            page.get_by_role("button", name="Termin verbindlich absagen").click()
            expect(page.locator(".detail-grid")).to_contain_text("Abgesagt")
            page.goto(base + "/kalender/neu/")
            fill(past, "09:00", "10:00", "completed")
            page.get_by_role("button", name="Termin speichern", exact=True).click()
            page.goto(base + f"/kundinnen/{customer.pk}/")
            expect(page.locator("#termine")).to_contain_text("1 tatsächlich abgeschlossener Besuch")
            page.locator("#termine").scroll_into_view_if_needed()
            page.screenshot(path=str(screenshots / "termine-kundenakte-pixel.png"), full_page=True)
            page.get_by_role("link", name="Alle Termine ansehen").click()
            expect(page.locator(".appointment-list-row")).to_have_count(3)
            for mode in ["tag", "woche", "monat"]:
                page.goto(base + f"/kalender/?ansicht={mode}&datum={tomorrow}")
                expect(page.get_by_role("heading", name="Dein Kalender.")).to_be_visible()
                if mode == "monat":
                    assert page.locator(".month-cell").count() in [28, 35, 42]
                else:
                    expect(page.locator(".calendar-day")).to_have_count(1 if mode == "tag" else 7)
                page.screenshot(
                    path=str(screenshots / f"kalender-{mode}-pixel.png"), full_page=True
                )
            page.goto(base + "/kalender/google/")
            expect(
                page.get_by_role("heading", name="Google ist noch nicht eingerichtet")
            ).to_be_visible()
            expect(page.locator('a[href^="haarvinci://google-connect"]')).to_have_count(0)
            page.screenshot(path=str(screenshots / "google-einrichtung-pixel.png"), full_page=True)
            for width in [360, 390, 412, 600, 760, 1024, 1440]:
                page.set_viewport_size({"width": width, "height": 915})
                for path in [
                    "/kalender/?ansicht=tag",
                    "/kalender/?ansicht=woche",
                    "/kalender/?ansicht=monat",
                    "/kalender/neu/",
                    "/kalender/google/",
                ]:
                    page.goto(base + path)
                    assert page.evaluate(
                        "document.documentElement.scrollWidth <= window.innerWidth"
                    ), f"Überlauf bei {width}px: {path}"
            page.goto(appointment)
            expect(page.locator(".detail-grid")).to_contain_text("90 Minuten")
            sessions.extend(
                cookie["value"] for cookie in context.cookies() if cookie["name"] == "sessionid"
            )
            assert not errors, errors
            browser.close()
        print(
            "Kalender-Oberfläche geprüft: Anlegen, Live-Dauer, Verschieben, Pufferwarnung, bestätigte Überschneidung, Absage, Besuchszählung, Kundenverknüpfung, drei Ansichten, Google-ohne-Konfiguration und sieben Bildschirmbreiten."
        )
    finally:
        Appointment.objects.filter(owner=user).delete()
        CalendarSettings.objects.filter(owner=user).delete()
        Customer.objects.filter(owner=user).delete()
        Session.objects.filter(session_key__in=sessions).delete()
        user.delete()


if __name__ == "__main__":
    main()
