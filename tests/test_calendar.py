from datetime import UTC, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from appointments.forms import AppointmentForm
from appointments.models import (
    Appointment,
    AppointmentType,
    DeviceCalendarConnection,
    DevicePrivateBusy,
)
from appointments.presentation import day_rows, entries_for_range
from customers.models import Customer, CustomerEvent


@override_settings(AXES_ENABLED=False, SECURE_SSL_REDIRECT=False)
class CalendarTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(
            "kalender-test", password="Fiktives-Testpasswort-2026!"
        )
        cls.other = get_user_model().objects.create_user("andere-kalender-test")
        cls.customer = Customer.objects.create(
            owner=cls.owner, first_name="Mila", last_name="Testgarten", email="mila@example.com"
        )
        cls.foreign = Customer.objects.create(
            owner=cls.other, first_name="Andere", last_name="Testkundin", email="andere@example.com"
        )
        cls.kind = AppointmentType.objects.filter(owner__isnull=True).first()

    def setUp(self):
        self.client.force_login(self.owner)

    def data(self, **overrides):
        return {
            "customer": self.customer.pk,
            "appointment_type": self.kind.pk,
            "day": (timezone.localdate() + timedelta(days=1)).isoformat(),
            "begin": "10:00",
            "finish": "11:30",
            "buffer_minutes": "15",
            "status": "planned",
            "notes": "Fiktiver Testtermin",
            "version": "1",
        } | overrides

    def create(self, **overrides):
        response = self.client.post(reverse("appointments:create"), self.data(**overrides))
        self.assertEqual(response.status_code, 302, getattr(response, "context", None))
        return Appointment.objects.latest("created_at")

    def test_create_duration_customer_and_audit_are_persistent(self):
        item = self.create(owner=self.other.pk)
        self.assertEqual(item.owner, self.owner)
        self.assertEqual(item.customer, self.customer)
        self.assertEqual(item.duration_minutes, 90)
        self.assertEqual(item.buffer_minutes, 15)
        self.assertEqual(self.customer.events.get().kind, "appointment_created")
        page = self.client.get(reverse("appointments:detail", args=[item.pk]))
        self.assertContains(page, "90 Minuten")
        self.assertContains(page, reverse("customers:detail", args=[self.customer.pk]))
        self.assertIn("no-store", page["Cache-Control"])

    def test_move_edit_and_cancel_are_audited(self):
        item = self.create()
        response = self.client.post(
            reverse("appointments:edit", args=[item.pk]),
            self.data(begin="12:00", finish="13:00", status="confirmed"),
        )
        self.assertEqual(response.status_code, 302)
        item.refresh_from_db()
        self.assertEqual(item.version, 2)
        self.assertEqual(timezone.localtime(item.start_at).hour, 12)
        url = reverse("appointments:cancel", args=[item.pk])
        self.assertContains(self.client.get(url), "Diesen Termin absagen?")
        item.refresh_from_db()
        self.assertEqual(item.status, "confirmed")
        self.assertEqual(self.client.post(url, {"version": 2}).status_code, 302)
        item.refresh_from_db()
        self.assertEqual(item.status, "cancelled")
        self.assertEqual(self.customer.events.count(), 3)
        self.assertTrue(self.customer.events.filter(kind="appointment_cancelled").exists())

    def test_stale_edit_and_cancellation_preserve_newer_version(self):
        item = self.create()
        edit = reverse("appointments:edit", args=[item.pk])
        self.client.post(edit, self.data(notes="Neuer Stand"))
        self.assertEqual(self.client.post(edit, self.data(notes="Alter Tab")).status_code, 409)
        self.assertEqual(
            self.client.post(
                reverse("appointments:cancel", args=[item.pk]), {"version": 1}
            ).status_code,
            409,
        )
        item.refresh_from_db()
        self.assertEqual(item.notes, "Neuer Stand")
        self.assertEqual(item.status, "planned")

    def test_overlap_requires_explicit_confirmation_and_respects_buffer(self):
        self.create()
        response = self.client.post(
            reverse("appointments:create"),
            self.data(begin="11:30", finish="12:00", buffer_minutes=0),
        )
        self.assertContains(response, "Zeit ist bereits belegt")
        self.assertEqual(Appointment.objects.count(), 1)
        self.create(begin="11:30", finish="12:00", buffer_minutes=0, allow_overlap="on")
        self.assertEqual(Appointment.objects.count(), 2)
        self.create(begin="12:00", finish="12:30", buffer_minutes=0)
        self.assertEqual(Appointment.objects.count(), 3)

    def test_cancelled_times_are_free_and_never_count_as_visits(self):
        self.create(status="cancelled")
        self.create(buffer_minutes=0)
        response = self.client.get(reverse("customers:detail", args=[self.customer.pk]))
        self.assertEqual(response.context["completed_visits"], 0)
        self.assertEqual(len(response.context["cancelled_appointments"]), 1)

    def test_completed_counts_and_last_next_are_real_status_based(self):
        past = (timezone.localdate() - timedelta(days=2)).isoformat()
        done = self.create(day=past, status="completed")
        self.create(day=(timezone.localdate() - timedelta(days=1)).isoformat(), status="cancelled")
        next_item = self.create()
        response = self.client.get(reverse("customers:detail", args=[self.customer.pk]))
        self.assertEqual(response.context["completed_visits"], 1)
        self.assertEqual(response.context["last_appointment"], done)
        self.assertEqual(response.context["next_appointment"], next_item)
        self.assertEqual(len(response.context["past_appointments"]), 1)

    def test_private_busy_is_generic_and_triggers_conflict(self):
        connection = DeviceCalendarConnection.objects.create(
            owner=self.owner, role="private", calendar_id="23", fingerprint="f" * 64
        )
        from datetime import time

        from appointments.forms import berlin_time

        day = timezone.localdate() + timedelta(days=1)
        DevicePrivateBusy.objects.create(
            connection=connection,
            start_at=berlin_time(day, time(10)),
            end_at=berlin_time(day, time(12)),
        )
        response = self.client.post(reverse("appointments:create"), self.data())
        self.assertContains(response, "Privat belegt")
        self.assertEqual(Appointment.objects.count(), 0)
        response = self.client.get(
            reverse("appointments:calendar"), {"ansicht": "tag", "datum": str(day)}
        )
        self.assertContains(response, "Privat belegt")
        self.assertNotContains(response, "private-test@example.com")

    def test_all_three_views_navigation_and_invalid_date(self):
        item = self.create()
        for mode in ["tag", "woche", "monat"]:
            response = self.client.get(
                reverse("appointments:calendar"),
                {"ansicht": mode, "datum": timezone.localdate(item.start_at).isoformat()},
            )
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "Mila")
            self.assertContains(response, "Nächster Zeitraum")
        self.assertEqual(
            self.client.get(
                reverse("appointments:calendar"), {"datum": "falsch", "ansicht": "falsch"}
            ).context["mode"],
            "woche",
        )
        leap = self.client.get(
            reverse("appointments:calendar"), {"ansicht": "monat", "datum": "2028-02-15"}
        )
        self.assertTrue(
            any(day["date"].isoformat() == "2028-02-29" for day in leap.context["days"])
        )

    def test_dst_nonexistent_and_ambiguous_times_are_rejected(self):
        for day in ["2026-03-29", "2026-10-25"]:
            form = AppointmentForm(
                data=self.data(day=day, begin="02:30", finish="04:00"), user=self.owner
            )
            self.assertFalse(form.is_valid())
            self.assertIn("Zeitumstellung", str(form.errors))

    def test_duration_uses_berlin_and_actual_elapsed_time_across_dst(self):
        for day, expected in [("2026-03-29", 60), ("2026-10-25", 180)]:
            item = self.create(day=day, begin="01:30", finish="03:30", buffer_minutes=0)
            self.assertEqual(item.duration_minutes, expected)
            response = self.client.get(
                reverse("appointments:duration"), {"datum": day, "beginn": "01:30", "ende": "03:30"}
            )
            self.assertEqual(response.json()["minutes"], expected)

    def test_invalid_fields_foreign_types_and_future_completed_are_rejected(self):
        foreign_kind = AppointmentType.objects.create(owner=self.other, name="Fremde Art")
        for bad in [
            {"customer": self.foreign.pk},
            {"appointment_type": foreign_kind.pk},
            {"begin": "12:00", "finish": "11:00"},
            {"buffer_minutes": -1},
            {"buffer_minutes": 241},
            {"status": "completed"},
            {"status": "unbekannt"},
            {"day": "kein Datum"},
            {"day": "1900-01-01"},
        ]:
            response = self.client.post(reverse("appointments:create"), self.data(**bad))
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["form"].errors)
        self.assertEqual(Appointment.objects.count(), 0)

    def test_owner_boundaries_for_read_edit_cancel_customer_list_and_filters(self):
        item = self.create()
        self.client.force_login(self.other)
        for name in ["detail", "edit", "cancel"]:
            self.assertEqual(
                self.client.get(reverse("appointments:" + name, args=[item.pk])).status_code, 404
            )
        self.assertEqual(
            self.client.post(reverse("appointments:edit", args=[item.pk]), self.data()).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(reverse("appointments:customer", args=[self.customer.pk])).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(
                reverse("appointments:calendar"), {"kundin": self.customer.pk}
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(reverse("appointments:create"), {"kundin": "falsch"}).status_code, 404
        )

    def test_login_csrf_and_unsafe_methods(self):
        item = self.create()
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.owner)
        for path in [
            reverse("appointments:create"),
            reverse("appointments:edit", args=[item.pk]),
            reverse("appointments:cancel", args=[item.pk]),
            reverse("appointments:google"),
        ]:
            self.assertEqual(Client().get(path).status_code, 302)
            self.assertEqual(csrf.post(path, self.data()).status_code, 403)
        self.assertEqual(self.client.post(reverse("appointments:calendar")).status_code, 405)

    def test_html_is_escaped_and_no_google_connection_is_faked(self):
        item = self.create(notes="<script>gefährlich</script>")
        page = self.client.get(reverse("appointments:detail", args=[item.pk]))
        self.assertContains(page, "&lt;script&gt;")
        self.assertNotContains(page, "<script>gefährlich</script>")
        settings = self.client.get(reverse("appointments:google"))
        self.assertContains(settings, "Kalender auf deinem Pixel")
        self.assertNotContains(settings, 'href="haarvinci://google-connect')

    def test_new_types_are_owner_specific_and_default_types_exist(self):
        self.assertEqual(AppointmentType.objects.filter(owner__isnull=True).count(), 7)
        self.assertEqual(
            self.client.post(
                reverse("appointments:type_create"), {"name": "Fiktive Spezialberatung"}
            ).status_code,
            302,
        )
        self.assertEqual(
            AppointmentType.objects.get(name="Fiktive Spezialberatung").owner, self.owner
        )
        self.client.force_login(self.other)
        self.assertNotContains(
            self.client.get(reverse("appointments:create")), "Fiktive Spezialberatung"
        )

    def test_buffer_crossing_midnight_is_not_presented_as_free(self):
        day = timezone.localdate() + timedelta(days=1)
        self.create(day=day.isoformat(), begin="23:00", finish="23:50", buffer_minutes=30)
        entries = entries_for_range(self.owner, day + timedelta(days=1), day + timedelta(days=1))
        rows = day_rows(day + timedelta(days=1), entries)
        self.assertTrue(
            any(
                row["kind"] == "buffer" and row["display_end"].astimezone(UTC).hour >= 0
                for row in rows
            )
        )
        self.assertEqual(rows[0]["kind"], "buffer")

    def test_service_failure_rolls_back_appointment_and_history(self):
        with patch("appointments.services.audit", side_effect=RuntimeError("Fiktiver Testfehler")):
            with self.assertRaises(RuntimeError):
                self.client.post(reverse("appointments:create"), self.data())
        self.assertEqual(Appointment.objects.count(), 0)
        self.assertEqual(CustomerEvent.objects.count(), 0)

    def test_legacy_broker_configuration_is_no_longer_exposed(self):
        url = reverse("appointments:google")
        response = self.client.get(url)
        self.assertNotContains(response, 'name="broker_url"')
        self.assertEqual(
            self.client.post(url, {"broker_url": "https://example.com"}).status_code, 405
        )

    @override_settings(DESKTOP_TOKEN="fiktiver-privater-app-schluessel")
    def test_native_google_entry_requires_both_gate_cookie_and_real_login(self):
        from appointments.google_api import GoogleError
        from appointments.native import authenticated_user

        session = self.client.session.session_key
        with self.assertRaises(GoogleError):
            authenticated_user("sessionid=" + session)
        with self.assertRaises(GoogleError):
            authenticated_user("haarvinci_android_gate=fiktiver-privater-app-schluessel")
        self.assertEqual(
            authenticated_user(
                "haarvinci_android_gate=fiktiver-privater-app-schluessel; "
                + __import__("django.conf", fromlist=["settings"]).settings.SESSION_COOKIE_NAME
                + "="
                + session
            ),
            self.owner,
        )

    def test_buffer_overlap_is_detected_across_spring_clock_change(self):
        self.create(day="2026-03-28", begin="23:00", finish="23:30", buffer_minutes=240)
        response = self.client.post(
            reverse("appointments:create"),
            self.data(day="2026-03-29", begin="04:00", finish="05:00", buffer_minutes=0),
        )
        self.assertContains(response, "Zeit ist bereits belegt")
        self.assertEqual(Appointment.objects.count(), 1)
