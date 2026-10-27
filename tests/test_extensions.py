from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from customers.forms import CustomerForm
from customers.models import Customer, CustomerEvent
from extensions.forms import PositionForm
from extensions.models import ExtensionPosition
from extensions.services import create_position


@override_settings(AXES_ENABLED=False, SECURE_SSL_REDIRECT=False)
class ExtensionsWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(
            "extensions-test", password="Fiktives-Testpasswort-2026!"
        )
        cls.other = get_user_model().objects.create_user("andere-test")
        cls.customer = Customer.objects.create(
            owner=cls.owner, first_name="Mila", last_name="Testgarten", email="mila@example.com"
        )
        cls.second = Customer.objects.create(
            owner=cls.owner, first_name="Nora", last_name="Testblume", email="nora@example.com"
        )
        cls.foreign = Customer.objects.create(
            owner=cls.other, first_name="Fremde", last_name="Testkundin", email="fremd@example.com"
        )

    def setUp(self):
        self.client.force_login(self.owner)

    def payload(self, **overrides):
        return {
            "manufacturer": "Fiktivhaar Atelier",
            "extension_type": "Tape-Ins",
            "color": "Naturblond",
            "color_code": "#18/22",
            "length_cm": "50,5",
            "weight_g": "100,25",
            "quantity": "4",
            "quantity_unit": "packs",
            "purchase_price": "149,90",
            "sale_price": "249,95",
            "assigned_on": "2026-10-01",
            "delivery_status": "ordered",
            "notes": "Nur erfundene Testposition.",
            "version": "1",
        } | overrides

    def create(self, customer=None, **overrides):
        customer = customer or self.customer
        response = self.client.post(
            reverse("customers:extension_create", args=[customer.pk]), self.payload(**overrides)
        )
        self.assertEqual(response.status_code, 302)
        return customer.extensions.latest("created_at")

    def route(self, name, position, customer=None):
        return reverse(
            "customers:extension_" + name, args=[(customer or self.customer).pk, position.pk]
        )

    def test_create_exact_decimals_fixed_customer_and_dated_history(self):
        position = self.create(customer_id=self.foreign.pk, owner=self.other.pk)
        self.assertEqual(position.customer, self.customer)
        self.assertEqual(position.length_cm, Decimal("50.5"))
        self.assertEqual(position.purchase_price, Decimal("149.90"))
        event = self.customer.events.get()
        self.assertEqual(event.occurred_on, date(2026, 10, 1))
        self.assertEqual(event.extension_uuid, position.pk)
        self.assertEqual(event.snapshot["purchase_price"], "149.90")
        self.assertEqual(event.actor, self.owner)
        self.assertEqual(event.kind, CustomerEvent.Kind.EXTENSION_CREATED)

    def test_multiple_independent_positions_and_zero_optional_price(self):
        first = self.create()
        second = self.create(
            manufacturer="Anderes Fiktivatelier",
            color="Kupfer",
            length_cm="40",
            purchase_price="0,20",
            sale_price="0",
            quantity="",
            quantity_unit="",
        )
        self.assertNotEqual(first.pk, second.pk)
        self.assertEqual(self.customer.extensions.count(), 2)
        self.assertEqual(second.sale_price, Decimal("0.00"))
        self.assertIsNone(second.quantity)
        self.assertEqual(self.customer.events.count(), 2)

    def test_edit_records_before_after_and_preserves_customer(self):
        position = self.create()
        path = self.route("edit", position)
        response = self.client.post(
            path,
            self.payload(
                color="Kupfer",
                purchase_price="159,15",
                delivery_status="received",
                customer_id=self.second.pk,
            ),
        )
        self.assertEqual(response.status_code, 302)
        position.refresh_from_db()
        self.assertEqual(position.customer, self.customer)
        self.assertEqual(position.version, 2)
        self.assertEqual(position.purchase_price, Decimal("159.15"))
        event = self.customer.events.get(kind=CustomerEvent.Kind.EXTENSION_UPDATED)
        changes = {entry["field"]: entry for entry in event.changes}
        self.assertEqual(changes["color"]["before"], "Naturblond")
        self.assertEqual(changes["color"]["after"], "Kupfer")
        self.assertEqual(changes["delivery_status"]["after"], "Geliefert")
        self.assertEqual(changes["purchase_price"]["after"], "159,15")
        self.assertEqual(event.snapshot["purchase_price"], "159.15")

    def test_stale_edit_and_stale_delete_do_not_overwrite(self):
        position = self.create()
        self.client.post(self.route("edit", position), self.payload(color="Kupfer"))
        response = self.client.post(self.route("edit", position), self.payload(color="Schwarz"))
        self.assertContains(response, "inzwischen geändert", status_code=409)
        response = self.client.post(self.route("delete", position), {"version": 1})
        self.assertEqual(response.status_code, 409)
        position.refresh_from_db()
        self.assertEqual(position.color, "Kupfer")
        self.assertEqual(self.customer.events.count(), 2)

    def test_deletion_needs_post_and_retains_snapshot(self):
        position = self.create()
        position_id = position.pk
        path = self.route("delete", position)
        self.assertContains(self.client.get(path), "Diese Position löschen?")
        self.assertTrue(ExtensionPosition.objects.filter(pk=position_id).exists())
        self.assertEqual(self.client.post(path, {"version": 1}).status_code, 302)
        self.assertFalse(ExtensionPosition.objects.filter(pk=position_id).exists())
        event = self.customer.events.get(kind=CustomerEvent.Kind.EXTENSION_DELETED)
        self.assertEqual(event.extension_uuid, position_id)
        self.assertEqual(event.snapshot["manufacturer"], "Fiktivhaar Atelier")
        response = self.client.get(reverse("customers:detail", args=[self.customer.pk]))
        self.assertContains(response, "Extensions gelöscht")
        self.assertContains(response, "Fiktivhaar Atelier")
        self.assertEqual(self.customer.events.count(), 2)

    def test_invalid_and_missing_versions_cannot_modify_or_delete(self):
        position = self.create()
        for version in ["", "abc", "-1"]:
            for action in ["edit", "delete"]:
                data = self.payload(version=version) if action == "edit" else {"version": version}
                self.assertEqual(
                    self.client.post(self.route(action, position), data).status_code, 200
                )
        position.refresh_from_db()
        self.assertEqual(position.version, 1)
        self.assertEqual(self.customer.events.count(), 1)

    def test_owner_and_customer_boundaries_for_all_actions(self):
        position = self.create()
        for action in ["edit", "delete"]:
            wrong = self.route(action, position, customer=self.second)
            self.assertEqual(self.client.get(wrong).status_code, 404)
            self.assertEqual(self.client.post(wrong, self.payload()).status_code, 404)
        self.client.force_login(self.other)
        for action in ["edit", "delete"]:
            self.assertEqual(self.client.get(self.route(action, position)).status_code, 404)
            self.assertEqual(
                self.client.post(self.route(action, position), self.payload()).status_code, 404
            )
        self.assertEqual(
            self.client.get(
                reverse("customers:extension_create", args=[self.customer.pk])
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(
                reverse("customers:extension_create", args=[self.customer.pk]), self.payload()
            ).status_code,
            404,
        )
        self.assertNotContains(self.client.get(reverse("extensions:list")), "Fiktivhaar Atelier")
        response = self.client.get(reverse("customers:extension_create", args=[self.foreign.pk]))
        self.assertNotContains(response, "Fiktivhaar Atelier")

    def test_login_and_csrf_are_required(self):
        position = self.create()
        paths = [
            reverse("extensions:list"),
            reverse("customers:extension_create", args=[self.customer.pk]),
            self.route("edit", position),
            self.route("delete", position),
        ]
        anonymous = Client()
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.owner)
        for path in paths:
            self.assertEqual(anonymous.get(path).status_code, 302)
            self.assertEqual(anonymous.post(path, self.payload()).status_code, 302)
            self.assertEqual(csrf.post(path, self.payload()).status_code, 403)
        self.assertEqual(self.customer.events.count(), 1)

    def test_server_validation_rejects_incomplete_and_invalid_values(self):
        for invalid in [
            {"manufacturer": ""},
            {"extension_type": ""},
            {"color": ""},
            {"length_cm": "0"},
            {"length_cm": "-5"},
            {"length_cm": "301"},
            {"weight_g": "0"},
            {"weight_g": "10001"},
            {"weight_g": "abc"},
            {"purchase_price": "-0,01"},
            {"purchase_price": "0,001"},
            {"purchase_price": "NaN"},
            {"sale_price": "-1"},
            {"quantity": "0"},
            {"quantity": "1.5"},
            {"quantity_unit": ""},
            {"quantity": ""},
            {"quantity_unit": "unknown"},
            {"delivery_status": "unknown"},
            {"assigned_on": ""},
            {"assigned_on": "kein Datum"},
        ]:
            with self.subTest(invalid=invalid):
                response = self.client.post(
                    reverse("customers:extension_create", args=[self.customer.pk]),
                    self.payload(**invalid),
                )
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["form"].errors)
        self.assertEqual(ExtensionPosition.objects.count(), 0)
        self.assertEqual(CustomerEvent.objects.count(), 0)

    def test_database_constraints_enforce_quantity_pair_and_prices(self):
        position = self.create()
        for changes in [
            {"quantity": None, "quantity_unit": "packs"},
            {"quantity": 2, "quantity_unit": ""},
            {"purchase_price": Decimal("-1")},
            {"length_cm": 0},
        ]:
            with (
                self.subTest(changes=changes),
                self.assertRaises(IntegrityError),
                transaction.atomic(),
            ):
                ExtensionPosition.objects.filter(pk=position.pk).update(**changes)

    def test_search_unicode_status_and_exact_totals(self):
        self.create(manufacturer="Fiktiv Üppig Weiß", purchase_price="0,10")
        self.create(
            manufacturer="Anderes Atelier", purchase_price="0,20", delivery_status="received"
        )
        for query in ["ÜPPIG", "WEISS", "#18/22", "MILA", "TAPE-INS", "Naturblond"]:
            response = self.client.get(reverse("extensions:list"), {"q": query})
            self.assertGreater(response.context["page"].paginator.count, 0)
        response = self.client.get(reverse("extensions:list"))
        self.assertEqual(response.context["purchase_total"], Decimal("0.30"))
        response = self.client.get(reverse("extensions:list"), {"status": "received"})
        self.assertEqual(response.context["page"].paginator.count, 1)
        self.assertEqual(response.context["purchase_total"], Decimal("0.20"))
        response = self.client.get(reverse("extensions:list"), {"q": "Gibtesnicht"})
        self.assertContains(response, "Keine passenden Extensions")

    def test_export_contains_profile_positions_and_deleted_audit_without_owner(self):
        position = self.create()
        self.client.post(self.route("delete", position), {"version": 1})
        data = self.client.get(reverse("customers:export", args=[self.customer.pk])).json()
        self.assertEqual(data["extensions"], [])
        self.assertEqual(len(data["history"]), 2)
        self.assertIn("natural_color", data["customer"])
        self.assertNotIn("owner", data["customer"])
        self.assertNotIn("actor", data["history"][0])

    def test_html_in_profile_extensions_and_history_is_escaped(self):
        self.create(manufacturer="<script>unsafe</script>", notes="<img src=x onerror=unsafe>")
        response = self.client.get(reverse("customers:detail", args=[self.customer.pk]))
        self.assertNotContains(response, "<script>unsafe</script>")
        self.assertNotContains(response, "<img src=x onerror=unsafe>")
        self.assertContains(response, "&lt;script&gt;unsafe&lt;/script&gt;")
        self.assertIn("no-store", response["Cache-Control"])

    def test_event_failure_rolls_back_position(self):
        form = PositionForm(data=self.payload())
        self.assertTrue(form.is_valid(), form.errors)
        with patch(
            "extensions.services.CustomerEvent.objects.create",
            side_effect=RuntimeError("Testfehler"),
        ):
            with self.assertRaises(RuntimeError):
                create_position(
                    customer_id=self.customer.pk, user=self.owner, cleaned_data=form.cleaned_data
                )
        self.assertEqual(ExtensionPosition.objects.count(), 0)

    def test_dated_events_are_chronological_and_paginated(self):
        self.create(assigned_on="2020-01-01")
        self.create(assigned_on="2026-01-01")
        dates = list(self.customer.events.values_list("occurred_on", flat=True))
        self.assertEqual(dates, [date(2026, 1, 1), date(2020, 1, 1)])
        for index in range(12):
            self.create(notes=f"Fiktive Position {index}")
        response = self.client.get(
            reverse("customers:detail", args=[self.customer.pk]), {"historie": 2}
        )
        self.assertEqual(len(response.context["history"]), 2)
        self.assertContains(response, "Seite 2 von 2")

    def test_optional_hair_profile_persists_and_is_audited(self):
        payload = {
            "first_name": "Mila",
            "last_name": "Testgarten",
            "email": "mila@example.com",
            "notes": "Persönliche Notiz bleibt.",
            "natural_color": "Dunkelblond",
            "current_color": "Kupfer",
            "natural_length": "25,5",
            "desired_length": "50",
            "hair_structure": "Wellig",
            "hair_density": "Feines Haar",
            "current_extensions": "Fiktive Tape-Ins",
            "hair_wishes": "Natürliche Fülle",
            "version": 1,
        }
        response = self.client.post(reverse("customers:edit", args=[self.customer.pk]), payload)
        self.assertEqual(response.status_code, 302)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.natural_length, Decimal("25.5"))
        self.assertEqual(self.customer.hair_structure, "Wellig")
        self.assertEqual(self.customer.notes, "Persönliche Notiz bleibt.")
        event = self.customer.events.get(kind=CustomerEvent.Kind.PROFILE)
        self.assertEqual(event.snapshot["desired_length"], "50")
        self.assertTrue(any(change["field"] == "hair_wishes" for change in event.changes))
        payload.update(version=2, natural_length="", desired_length="")
        self.client.post(reverse("customers:edit", args=[self.customer.pk]), payload)
        self.customer.refresh_from_db()
        self.assertIsNone(self.customer.natural_length)
        self.assertEqual(self.customer.events.count(), 2)

    def test_hair_profile_is_optional_and_length_is_validated(self):
        basic = {"first_name": "Mila", "last_name": "Testgarten", "email": "mila@example.com"}
        self.assertTrue(CustomerForm(data=basic).is_valid())
        for length in ["-1", "301", "NaN", "Text"]:
            self.assertFalse(CustomerForm(data=basic | {"natural_length": length}).is_valid())
