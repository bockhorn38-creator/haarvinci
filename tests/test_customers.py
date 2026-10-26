from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from customers.models import Customer


@override_settings(AXES_ENABLED=False, SECURE_SSL_REDIRECT=False)
class CustomerWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(
            username="testconny", password="Test-Passwort-2026!", first_name="Conny"
        )
        cls.other = get_user_model().objects.create_user(
            username="andere", password="Weiteres-Testpasswort!"
        )
        cls.customer = Customer.objects.create(
            owner=cls.owner,
            first_name="Marie",
            last_name="Sommer",
            phone="+49 151 0000 0101",
            email="marie@example.com",
            notes="Nur eine erfundene Testkundin.",
        )

    def setUp(self):
        self.client.force_login(self.owner)

    def payload(self, **overrides):
        data = {
            "first_name": "Nora",
            "last_name": "Testblume",
            "phone": "+49 151 0000 0123",
            "email": "nora@example.com",
            "street": "Testweg 1",
            "postal_code": "12345",
            "city": "Beispielstadt",
            "birthday": "1990-05-07",
            "first_consultation": "2026-01-01",
            "notes": "Fiktive Notiz",
            "version": "1",
        }
        return data | overrides

    def test_all_customer_pages_require_login(self):
        client = Client()
        paths = [
            reverse("dashboard"),
            reverse("customers:list"),
            reverse("customers:create"),
            reverse("customers:detail", args=[self.customer.pk]),
            reverse("customers:edit", args=[self.customer.pk]),
            reverse("customers:export", args=[self.customer.pk]),
            reverse("account"),
        ]
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(client.get(path).status_code, 302)
                self.assertEqual(client.post(path, self.payload()).status_code, 302)

    def test_create_persists_and_ignores_supplied_owner(self):
        response = self.client.post(
            reverse("customers:create"), self.payload(owner=self.other.pk), follow=True
        )
        self.assertEqual(response.status_code, 200)
        customer = Customer.objects.get(last_name="Testblume")
        self.assertEqual(customer.owner, self.owner)
        self.assertEqual(customer.phone_digits, "4915100000123")
        self.assertContains(response, "Fiktive Notiz")
        self.assertEqual(customer.birthday, date(1990, 5, 7))

    def test_edit_persists_and_increments_version(self):
        response = self.client.post(
            reverse("customers:edit", args=[self.customer.pk]),
            self.payload(notes="Neu gespeichert"),
        )
        self.assertEqual(response.status_code, 302)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.notes, "Neu gespeichert")
        self.assertEqual(self.customer.version, 2)

    def test_stale_form_cannot_overwrite_changes(self):
        path = reverse("customers:edit", args=[self.customer.pk])
        self.client.post(path, self.payload(notes="Erster Stand"))
        response = self.client.post(path, self.payload(notes="Alter Tab"))
        self.assertEqual(response.status_code, 409)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.notes, "Erster Stand")
        self.assertContains(response, "inzwischen geändert", status_code=409)

    def test_version_required_for_edit(self):
        response = self.client.post(
            reverse("customers:edit", args=[self.customer.pk]), self.payload(version="")
        )
        self.assertEqual(response.status_code, 200)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.version, 1)
        self.assertContains(response, "Bearbeitungsstand fehlt")

    def test_user_isolation_for_read_write_search_and_export(self):
        self.client.force_login(self.other)
        for route in ["customers:detail", "customers:edit", "customers:export"]:
            path = reverse(route, args=[self.customer.pk])
            self.assertEqual(self.client.get(path).status_code, 404)
            self.assertEqual(
                self.client.post(path, self.payload()).status_code,
                404 if route == "customers:edit" else 405,
            )
        self.assertNotContains(self.client.get(reverse("customers:list")), "Sommer")
        self.assertEqual(
            self.client.get(reverse("customers:list"), {"q": "Sommer"})
            .context["page"]
            .paginator.count,
            0,
        )
        self.assertEqual(self.client.get(reverse("dashboard")).context["customer_count"], 0)

    def test_search_by_name_email_and_unformatted_phone(self):
        for query in ["marie sommer", "SOMMER", "marie@example.com", "4915100000101"]:
            with self.subTest(query=query):
                response = self.client.get(reverse("customers:list"), {"q": query})
                self.assertContains(response, "Marie Sommer")
                self.assertEqual(response.context["page"].paginator.count, 1)

    def test_empty_search_result(self):
        response = self.client.get(reverse("customers:list"), {"q": "ExistiertNicht"})
        self.assertContains(response, "Noch keine passende Verbindung")
        self.assertEqual(response.context["page"].paginator.count, 0)

    def test_invalid_data_not_saved(self):
        for invalid in [
            self.payload(first_name=""),
            self.payload(phone="", email=""),
            self.payload(email="keine-email"),
            self.payload(phone="abc"),
            self.payload(birthday=str(timezone.localdate() + timedelta(days=1))),
            self.payload(first_consultation="1980-01-01"),
        ]:
            with self.subTest(invalid=invalid):
                count = Customer.objects.count()
                response = self.client.post(reverse("customers:create"), invalid)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["form"].errors)
                self.assertEqual(Customer.objects.count(), count)

    def test_email_only_contact_is_supported(self):
        self.client.post(reverse("customers:create"), self.payload(phone=""))
        self.assertTrue(Customer.objects.filter(last_name="Testblume", phone="").exists())

    def test_notes_are_escaped(self):
        self.customer.notes = '<script>alert("test")</script>'
        self.customer.save()
        response = self.client.get(reverse("customers:detail", args=[self.customer.pk]))
        self.assertContains(response, "&lt;script&gt;")
        self.assertNotContains(response, '<script>alert("test")</script>')

    def test_export_is_private_and_contains_saved_data(self):
        response = self.client.get(reverse("customers:export", args=[self.customer.pk]))
        self.assertEqual(response.json()["customer"]["email"], "marie@example.com")
        self.assertEqual(response.json()["format_version"], 1)
        self.assertNotIn("owner", response.json()["customer"])
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn("no-store", response["Cache-Control"])

    def test_csrf_is_required(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        self.assertEqual(client.post(reverse("customers:create"), self.payload()).status_code, 403)
        self.assertEqual(Customer.objects.count(), 1)

    def test_private_pages_security_headers(self):
        response = self.client.get(reverse("customers:list"))
        self.assertIn("no-store", response["Cache-Control"])
        self.assertIn("frame-ancestors 'none'", response["Content-Security-Policy"])
        self.assertEqual(response["X-Frame-Options"], "DENY")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")

    def test_pagination_preserves_all_records(self):
        for index in range(14):
            Customer.objects.create(
                owner=self.owner,
                first_name="Test",
                last_name=f"Kundin {index:02}",
                email=f"test{index}@example.com",
            )
        first = self.client.get(reverse("customers:list"))
        second = self.client.get(reverse("customers:list"), {"seite": 2})
        self.assertEqual(len(first.context["page"]), 12)
        self.assertEqual(len(second.context["page"]), 3)
        self.assertEqual(first.context["page"].paginator.count, 15)

    def test_password_change_invalidates_old_password(self):
        response = self.client.post(
            reverse("password_change"),
            {
                "old_password": "Test-Passwort-2026!",
                "new_password1": "Neues-Sicheres-Passwort-2026!",
                "new_password2": "Neues-Sicheres-Passwort-2026!",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.owner.refresh_from_db()
        self.assertFalse(self.owner.check_password("Test-Passwort-2026!"))
        self.assertTrue(self.owner.check_password("Neues-Sicheres-Passwort-2026!"))
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 200)

    def test_logout_requires_post_and_protects_data_after_logout(self):
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        self.assertEqual(self.client.post(reverse("logout")).status_code, 302)
        self.assertEqual(self.client.get(reverse("customers:list")).status_code, 302)

    def test_health_checks_database(self):
        self.assertEqual(Client().get(reverse("health")).json(), {"status": "ok"})

    def test_manifest_supports_android(self):
        response = self.client.get(reverse("manifest"))
        import json

        data = json.loads(response.content)
        self.assertEqual(data["display"], "standalone")
        self.assertEqual(data["lang"], "de")


@override_settings(SECURE_SSL_REDIRECT=False, AXES_ENABLED=True)
class AuthenticationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="conny-test", password="Test-Passwort-2026!"
        )

    def test_repeated_failed_login_is_limited(self):
        for _ in range(5):
            self.client.post(reverse("login"), {"username": "conny-test", "password": "falsch"})
        response = self.client.post(
            reverse("login"), {"username": "conny-test", "password": "Test-Passwort-2026!"}
        )
        self.assertEqual(response.status_code, 429)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertContains(response, "Sicherheitspause", status_code=429)

    def test_login_prevents_external_redirect(self):
        response = self.client.post(
            reverse("login"),
            {
                "username": "conny-test",
                "password": "Test-Passwort-2026!",
                "next": "https://example.org/fremd",
            },
        )
        self.assertRedirects(response, reverse("dashboard"))

    def test_password_is_hashed(self):
        self.assertNotEqual(self.user.password, "Test-Passwort-2026!")
        self.assertTrue(self.user.check_password("Test-Passwort-2026!"))
