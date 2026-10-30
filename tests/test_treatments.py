import uuid
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from appointments.models import Appointment, AppointmentType
from customers.models import Customer, CustomerEvent
from customers.services import EditConflict
from extensions.models import ExtensionPosition
from treatments.forms import PaymentForm, TreatmentForm
from treatments.models import Payment, PriceOption, Treatment
from treatments.reports import report
from treatments.services import (
    BusinessError,
    book_payment,
    cancel_treatment,
    quote,
    save_treatment,
    void_payment,
)


@override_settings(AXES_ENABLED=False, SECURE_SSL_REDIRECT=False)
class TreatmentTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("fiktiv-salon")
        self.other = get_user_model().objects.create_user("fremd-salon")
        self.customer = Customer.objects.create(
            owner=self.user,
            first_name="Mila",
            last_name="Behandlungsfiktiv",
            email="mila@example.com",
            natural_color="Braun",
            desired_length=50,
        )
        self.foreign = Customer.objects.create(
            owner=self.other, first_name="Andere", last_name="Fiktiv", email="andere@example.com"
        )
        self.tariffs = [
            PriceOption.objects.create(
                owner=self.user,
                name=f"Fiktivpreis {rows} Reihen",
                category="weaving",
                rows=rows,
                price=price,
            )
            for rows, price in [(1, "80.00"), (2, "145.00"), (3, "210.00")]
        ]
        self.wash = PriceOption.objects.create(
            owner=self.user, name="Fiktive Haarwäsche", category="service", price="20.00"
        )
        self.cut = PriceOption.objects.create(
            owner=self.user, name="Fiktiver Schnitt", category="service", price="15.50"
        )
        self.position = ExtensionPosition.objects.create(
            customer=self.customer,
            manufacturer="Fiktivhaar",
            extension_type="Tressen",
            color="Braun",
            length_cm=50,
            weight_g=100,
            purchase_price="50.00",
            sale_price="100.00",
        )
        self.client.force_login(self.user)

    def raw(self, **changes):
        return {
            "creation_key": str(uuid.uuid4()),
            "customer": str(self.customer.pk),
            "performed_on": str(timezone.localdate()),
            "description": "Weaving fiktiv",
            "status": "planned",
            "rows": "2",
            "price_mode": "weaving",
            "services": [str(self.wash.pk)],
            "extensions": [str(self.position.pk)],
            "notes": "Fiktive Dokumentation.",
        } | changes

    def data(self, **changes):
        form = TreatmentForm(self.raw(**changes), user=self.user)
        self.assertTrue(form.is_valid(), form.errors)
        return form.cleaned_data

    def create(self, **changes):
        data = self.data(**changes)
        return save_treatment(
            user=self.user, data=data, expected_quote=quote(self.user, data)["digest"]
        )

    def payment(self, item, amount="50.00", refund=False, **changes):
        item.refresh_from_db()
        data = {
            "amount": amount,
            "booked_on": str(timezone.localdate()),
            "method": "cash",
            "purpose": "refund" if refund else "deposit",
            "booking_key": str(uuid.uuid4()),
            "version": str(item.version),
            "notes": "Fiktive Rückgabe" if refund else "",
        } | changes
        form = PaymentForm(data, user=self.user, treatment=item, refund=refund)
        self.assertTrue(form.is_valid(), form.errors)
        return book_payment(
            user=self.user, treatment_id=item.pk, data=form.cleaned_data, refund=refund
        )

    def test_row_tariffs_extras_and_optional_extension_prices(self):
        for rows, expected in [(1, "100.00"), (2, "165.00"), (3, "230.00")]:
            with self.subTest(rows=rows):
                item = self.create(rows=str(rows))
                self.assertEqual(item.total, Decimal(expected))
        item = self.create(services=[str(self.wash.pk), str(self.cut.pk)], charge_extensions="on")
        self.assertEqual(item.total, Decimal("280.50"))
        self.assertEqual(sum(line.amount for line in item.lines.all()), item.total)
        self.assertEqual(item.extension_links.get().position, self.position)

    def test_individual_price_is_total_not_added_twice(self):
        item = self.create(
            price_mode="individual",
            custom_price="199,95",
            services=[str(self.wash.pk), str(self.cut.pk)],
            charge_extensions="on",
        )
        self.assertEqual(item.total, Decimal("199.95"))
        self.assertEqual(sum(line.amount for line in item.lines.all()), Decimal("199.95"))
        self.assertTrue(item.lines.filter(amount__lt=0).exists())
        free = self.create(price_mode="individual", custom_price="0", rows="", services=[])
        self.assertEqual(free.total, 0)

    def test_unknown_row_tariff_and_missing_material_price_are_rejected(self):
        with self.assertRaises(BusinessError):
            self.create(rows="5")
        self.position.sale_price = None
        self.position.save()
        with self.assertRaises(BusinessError):
            self.create(charge_extensions="on")
        self.assertFalse(Treatment.objects.exists())

    def test_price_snapshot_survives_catalog_changes_and_extension_deletion(self):
        item = self.create()
        self.tariffs[1].price = 999
        self.tariffs[1].version += 1
        self.tariffs[1].save()
        self.position.delete()
        item.refresh_from_db()
        self.assertEqual(item.total, Decimal("165.00"))
        self.assertIsNone(item.extension_links.get().position)
        self.assertIn("Fiktivhaar", item.extension_links.get().label)
        self.assertTrue(item.lines.filter(amount=145).exists())

    def test_quote_changed_before_confirmation_is_rejected(self):
        data = self.data()
        digest = quote(self.user, data)["digest"]
        self.wash.price = 30
        self.wash.version += 1
        self.wash.save()
        with self.assertRaises(BusinessError):
            save_treatment(user=self.user, data=data, expected_quote=digest)
        self.assertFalse(Treatment.objects.exists())

    def test_deposit_partials_full_payment_and_overpayment(self):
        item = self.create()
        self.payment(item, "50,00")
        self.assertEqual(item.outstanding, Decimal("115.00"))
        self.payment(item, "65.00", purpose="partial")
        self.assertEqual(item.outstanding, Decimal("50.00"))
        self.payment(item, "50", purpose="final")
        self.assertEqual(item.outstanding, 0)
        with self.assertRaises(BusinessError):
            self.payment(item, "0.01")
        self.assertEqual(item.payments.count(), 3)
        stats = report(self.user)
        self.assertEqual(stats["net_received"], 165)
        self.assertEqual(stats["completed_value"], 0)
        self.assertEqual(stats["outstanding"], 0)

    def test_multiple_extensions_do_not_multiply_statistics(self):
        second = ExtensionPosition.objects.create(
            customer=self.customer,
            manufacturer="Fiktivhaar 2",
            extension_type="Tressen",
            color="Blond",
            length_cm=40,
            weight_g=80,
            purchase_price=30,
            sale_price=70,
        )
        item = self.create(extensions=[str(self.position.pk), str(second.pk)], status="completed")
        self.payment(item, "50")
        stats = report(self.user, self.customer)
        self.assertEqual(stats["completed_count"], 1)
        self.assertEqual(stats["completed_value"], 165)
        self.assertEqual(stats["receipts"], 50)
        self.assertEqual(stats["outstanding"], 115)

    def test_payment_double_click_idempotency_and_reused_key_guard(self):
        item = self.create()
        entry = self.payment(item)
        data = {
            "amount": entry.amount,
            "booked_on": entry.booked_on,
            "method": entry.method,
            "purpose": entry.purpose,
            "booking_key": entry.booking_key,
            "version": 1,
            "notes": "",
        }
        again = book_payment(user=self.user, treatment_id=item.pk, data=data)
        self.assertEqual(entry.pk, again.pk)
        self.assertEqual(Payment.objects.count(), 1)
        with self.assertRaises(BusinessError):
            book_payment(
                user=self.user, treatment_id=item.pk, data=data | {"amount": Decimal("1.00")}
            )

    def test_treatment_cancellation_and_refunds_have_clear_balances(self):
        item = self.create(status="completed")
        incoming = self.payment(item, "100")
        item.refresh_from_db()
        cancel_treatment(
            user=self.user, treatment_id=item.pk, version=item.version, reason="Fiktive Stornierung"
        )
        item.refresh_from_db()
        self.assertEqual(item.outstanding, 0)
        self.assertEqual(item.refund_due, 100)
        with self.assertRaises(BusinessError):
            self.payment(item, "10")
        self.payment(item, "30", refund=True, original=str(incoming.pk))
        self.assertEqual(item.refund_due, 70)
        self.payment(item, "70", refund=True, original=str(incoming.pk))
        self.assertEqual(item.refund_due, 0)
        with self.assertRaises(BusinessError):
            self.payment(item, "1", refund=True, original=str(incoming.pk))
        stats = report(self.user)
        self.assertEqual(
            (
                stats["completed_count"],
                stats["completed_value"],
                stats["outstanding"],
                stats["net_received"],
            ),
            (0, 0, 0, 0),
        )
        self.assertEqual(stats["refunds"], 100)
        self.assertEqual(Payment.objects.count(), 3)

    def test_refund_original_is_owner_and_treatment_scoped(self):
        item = self.create()
        receipt = self.payment(item)
        other_item = self.create(description="Anderer Vorgang")
        form = PaymentForm(
            {
                "amount": "1",
                "booked_on": str(timezone.localdate()),
                "method": "cash",
                "purpose": "refund",
                "booking_key": uuid.uuid4(),
                "original": receipt.pk,
                "notes": "Test",
            },
            user=self.user,
            treatment=other_item,
            refund=True,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("original", form.errors)

    def test_void_is_correction_not_cash_refund(self):
        item = self.create()
        receipt = self.payment(item)
        item.refresh_from_db()
        void_payment(
            user=self.user,
            payment_id=receipt.pk,
            version=item.version,
            reason="Fiktiver Erfassungsfehler",
        )
        self.assertEqual(item.net_paid, 0)
        self.assertEqual(item.outstanding, 165)
        self.assertEqual(report(self.user)["refunds"], 0)
        self.assertEqual(Payment.objects.get().state, "voided")
        self.assertTrue(CustomerEvent.objects.filter(kind="payment_voided").exists())

    def test_receipt_with_refund_cannot_be_voided_until_refund_is_corrected(self):
        item = self.create()
        receipt = self.payment(item, "100")
        refund = self.payment(item, "20", refund=True, original=receipt.pk)
        item.refresh_from_db()
        with self.assertRaises(BusinessError):
            void_payment(user=self.user, payment_id=receipt.pk, version=item.version, reason="Test")
        void_payment(
            user=self.user, payment_id=refund.pk, version=item.version, reason="Fiktiver Fehler"
        )
        self.assertEqual(item.net_paid, 100)
        item.refresh_from_db()
        void_payment(
            user=self.user, payment_id=receipt.pk, version=item.version, reason="Fiktiver Fehler"
        )
        self.assertEqual(item.net_paid, 0)

    def test_refund_reopens_due_and_price_cannot_drop_below_paid(self):
        item = self.create()
        incoming = self.payment(item, "165")
        item.refresh_from_db()
        data = self.data(price_mode="individual", custom_price="100") | {"version": item.version}
        with self.assertRaises(BusinessError):
            save_treatment(user=self.user, treatment_id=item.pk, data=data)
        self.payment(item, "65", refund=True, original=incoming.pk)
        self.assertEqual(item.outstanding, 65)
        item.refresh_from_db()
        save_treatment(user=self.user, treatment_id=item.pk, data=data | {"version": item.version})
        item.refresh_from_db()
        self.assertEqual((item.total, item.outstanding), (100, 0))

    def test_linked_appointment_completes_once_and_visits_are_not_duplicated(self):
        start = timezone.now() - timedelta(days=1)
        appointment = Appointment.objects.create(
            owner=self.user,
            customer=self.customer,
            appointment_type=AppointmentType.objects.first(),
            start_at=start,
            end_at=start + timedelta(hours=1),
        )
        item = self.create(
            appointment=appointment.pk,
            status="completed",
            performed_on=str(timezone.localdate(start)),
        )
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, "completed")
        self.assertEqual(report(self.user, self.customer)["visits"], 1)
        self.assertEqual(
            self.client.get(reverse("customers:detail", args=[self.customer.pk])).context[
                "completed_visits"
            ],
            1,
        )
        with self.assertRaises(BusinessError):
            self.create(appointment=appointment.pk)
        cancel_treatment(
            user=self.user, treatment_id=item.pk, version=item.version, reason="Fiktiv"
        )
        self.assertEqual(report(self.user, self.customer)["visits"], 0)

    def test_old_completed_appointment_still_counts_without_treatment(self):
        start = timezone.now() - timedelta(days=3)
        Appointment.objects.create(
            owner=self.user,
            customer=self.customer,
            appointment_type=AppointmentType.objects.first(),
            start_at=start,
            end_at=start + timedelta(hours=1),
            status="completed",
        )
        self.assertEqual(report(self.user, self.customer)["visits"], 1)
        self.assertEqual(report(self.user, self.customer)["completed_value"], 0)

    def test_future_treatment_and_customer_mismatch_are_rejected(self):
        form = TreatmentForm(
            self.raw(
                status="completed", performed_on=str(timezone.localdate() + timedelta(days=1))
            ),
            user=self.user,
        )
        self.assertFalse(form.is_valid())
        foreign = TreatmentForm(self.raw(customer=self.foreign.pk), user=self.user)
        self.assertFalse(foreign.is_valid())
        self.assertIn("customer", foreign.errors)
        data = self.data() | {"customer": self.foreign}
        with self.assertRaises(Customer.DoesNotExist):
            save_treatment(user=self.user, data=data)

    def test_concurrent_edit_and_payment_versions(self):
        item = self.create()
        stale = item.version
        self.payment(item)
        with self.assertRaises(EditConflict):
            cancel_treatment(user=self.user, treatment_id=item.pk, version=stale, reason="Fiktiv")
        with self.assertRaises(EditConflict):
            save_treatment(
                user=self.user, treatment_id=item.pk, data=self.data() | {"version": stale}
            )

    def test_money_date_and_required_field_validation(self):
        item = self.create()
        for amount in ["-1", "0", "1,001", "NaN", "Infinity", "10000000"]:
            form = PaymentForm(
                {
                    "amount": amount,
                    "booked_on": str(timezone.localdate()),
                    "method": "cash",
                    "purpose": "deposit",
                    "booking_key": uuid.uuid4(),
                },
                user=self.user,
                treatment=item,
            )
            self.assertFalse(form.is_valid(), amount)
        for bad in [
            {"method": "bitcoin"},
            {"booked_on": str(timezone.localdate() + timedelta(days=1))},
        ]:
            form = PaymentForm(
                {
                    "amount": "1",
                    "booked_on": str(timezone.localdate()),
                    "method": "cash",
                    "purpose": "deposit",
                    "booking_key": uuid.uuid4(),
                }
                | bad,
                user=self.user,
                treatment=item,
            )
            self.assertFalse(form.is_valid())

    def test_transaction_failure_rolls_back_price_links_and_history(self):
        with patch("treatments.services.event", side_effect=RuntimeError("Fiktiver Fehler")):
            with self.assertRaises(RuntimeError):
                self.create()
        self.assertFalse(Treatment.objects.exists())
        self.assertFalse(CustomerEvent.objects.exists())

    def test_dates_in_reports_distinguish_service_from_cash_and_global_debts(self):
        old = timezone.localdate() - timedelta(days=10)
        item = self.create(status="completed", performed_on=str(old))
        self.payment(item, "50")
        stats = report(self.user, start=timezone.localdate(), end=timezone.localdate())
        self.assertEqual(
            (
                stats["completed_count"],
                stats["completed_value"],
                stats["receipts"],
                stats["outstanding"],
            ),
            (0, 0, 50, 115),
        )
        self.assertEqual(report(self.other)["receipts"], 0)
        self.assertEqual(report(self.other)["outstanding"], 0)

    def test_http_flow_requires_price_preview_and_confirmation(self):
        url = reverse("treatments:create") + "?kundin=" + str(self.customer.pk)
        self.assertContains(self.client.get(url), "Behandlung erfassen")
        raw = self.raw()
        response = self.client.post(url, raw | {"action": "preview"})
        self.assertContains(response, "Deine Preisübersicht")
        self.assertFalse(Treatment.objects.exists())
        response = self.client.post(url, raw | {"action": "save"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Treatment.objects.exists())
        digest = quote(self.user, self.data())["digest"]
        response = self.client.post(url, raw | {"action": "save", "quote_digest": digest})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Treatment.objects.exists())

    def test_appointment_cancellation_cascades_only_planned_treatment(self):
        from appointments.services import cancel_appointment

        start = timezone.now() + timedelta(days=1)
        appointment = Appointment.objects.create(
            owner=self.user,
            customer=self.customer,
            appointment_type=AppointmentType.objects.first(),
            start_at=start,
            end_at=start + timedelta(hours=1),
        )
        item = self.create(appointment=appointment.pk)
        self.payment(item, "50")
        cancel_appointment(
            user=self.user, appointment_id=appointment.pk, version=appointment.version
        )
        item.refresh_from_db()
        self.assertEqual(item.status, "cancelled")
        self.assertEqual(item.refund_due, 50)
        self.assertEqual(Payment.objects.count(), 1)

    def test_linked_appointment_customer_cannot_be_reassigned(self):
        from appointments.forms import AppointmentForm

        start = timezone.now() + timedelta(days=1)
        appointment = Appointment.objects.create(
            owner=self.user,
            customer=self.customer,
            appointment_type=AppointmentType.objects.first(),
            start_at=start,
            end_at=start + timedelta(hours=1),
        )
        self.create(appointment=appointment.pk)
        other = Customer.objects.create(
            owner=self.user, first_name="Andere", last_name="Fiktiv", email="andere.own@example.com"
        )
        form = AppointmentForm(
            {
                "customer": other.pk,
                "appointment_type": appointment.appointment_type_id,
                "version": appointment.version,
                "day": str(timezone.localdate(start)),
                "begin": "10:00",
                "finish": "11:00",
                "status": "planned",
                "buffer_minutes": 0,
            },
            instance=appointment,
            user=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("customer", form.errors)

    def test_keeping_price_allows_notes_after_service_is_deactivated(self):
        item = self.create()
        self.wash.active = False
        self.wash.save()
        raw = self.raw(price_mode="keep", version=item.version, notes="Neue fiktive Notiz")
        form = TreatmentForm(raw, user=self.user, instance=item)
        self.assertTrue(form.is_valid(), form.errors)
        updated = save_treatment(user=self.user, treatment_id=item.pk, data=form.cleaned_data)
        self.assertEqual(updated.total, Decimal("165.00"))
        self.assertEqual(updated.notes, "Neue fiktive Notiz")

    def test_final_payment_must_actually_settle_all_remaining_money(self):
        item = self.create()
        with self.assertRaises(BusinessError):
            self.payment(item, "1", purpose="final")
        self.assertFalse(item.payments.exists())

    def test_customer_export_contains_prices_relationships_and_money(self):
        import json

        item = self.create()
        self.payment(item)
        response = self.client.get(reverse("customers:export", args=[self.customer.pk]))
        data = json.loads(response.content)
        self.assertEqual(len(data["treatments"]), 1)
        self.assertEqual(len(data["payments"]), 1)
        self.assertEqual(data["payments"][0]["treatment_id"], str(item.pk))
        self.assertEqual(len(data["treatment_extensions"]), 1)
        self.assertEqual(len(data["treatment_price_lines"]), 2)

    def test_treatment_double_click_is_idempotent_without_appointment(self):
        data = self.data()
        pricing = quote(self.user, data)
        first = save_treatment(user=self.user, data=data, expected_quote=pricing["digest"])
        second = save_treatment(user=self.user, data=data, expected_quote=pricing["digest"])
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(Treatment.objects.count(), 1)
        with self.assertRaises(BusinessError):
            save_treatment(
                user=self.user,
                data=data | {"notes": "Anderer Inhalt"},
                expected_quote=pricing["digest"],
            )

    def test_cross_owner_views_and_csrf_are_protected(self):
        item = self.create()
        entry = self.payment(item)
        self.client.force_login(self.other)
        for name, key in [
            ("detail", item.pk),
            ("edit", item.pk),
            ("payment", item.pk),
            ("cancel", item.pk),
            ("void", entry.pk),
        ]:
            self.assertEqual(
                self.client.get(reverse("treatments:" + name, args=[key])).status_code, 404
            )
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.user)
        self.assertEqual(
            strict.post(
                reverse("treatments:cancel", args=[item.pk]),
                {"version": item.version, "reason": "Test"},
            ).status_code,
            403,
        )
        self.client.logout()
        self.assertEqual(self.client.get(reverse("treatments:list")).status_code, 302)
