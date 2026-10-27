import copy
import json
import uuid
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.http import QueryDict
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from appointments.models import Appointment
from customers.models import Customer, CustomerEvent
from extensions.models import ExtensionPosition
from intake.models import ImportReceipt
from intake.parser import ImportProblem, parse
from intake.services import DRAFTS, commit, find, prepare, review


def bundle():
    day = (timezone.localdate() + timedelta(days=5)).isoformat()
    return {
        "format": "haarvinci.import",
        "version": 1,
        "id": str(uuid.uuid4()),
        "customers": [
            {
                "ref": "k1",
                "mode": "new",
                "data": {
                    "first_name": "Lina",
                    "last_name": "Fiktivblüte",
                    "email": "lina.import@example.com",
                    "natural_color": "Dunkelblond",
                    "desired_length": "50,5",
                },
            }
        ],
        "extensions": [
            {
                "customer_ref": "k1",
                "data": {
                    "manufacturer": "Fiktivhaar",
                    "extension_type": "Tape-Ins",
                    "color": "Blond",
                    "length_cm": "50,5",
                    "weight_g": "100,25",
                    "purchase_price": "149,90",
                    "assigned_on": day,
                },
            }
        ],
        "appointments": [
            {
                "customer_ref": "k1",
                "data": {
                    "appointment_type": "Erstberatung",
                    "day": day,
                    "begin": "10:00",
                    "finish": "11:00",
                    "buffer_minutes": "15",
                    "status": "planned",
                },
            }
        ],
    }


def posted_forms(result):
    posted = QueryDict(mutable=True)
    for entry in result["customers"]:
        for form in [entry["target"], entry["form"]]:
            for name in form.fields:
                value = form.data.get(form.add_prefix(name), "")
                posted[form.add_prefix(name)] = value
    for key in ["positions", "appointments"]:
        for entry in result[key]:
            form = entry["form"]
            for name in form.fields:
                posted[form.add_prefix(name)] = form.data.get(form.add_prefix(name), "")
    posted["action"] = "review"
    return posted


@override_settings(DEBUG=True, AXES_ENABLED=False, SECURE_SSL_REDIRECT=False)
class ImportTests(TestCase):
    def setUp(self):
        DRAFTS.clear()
        self.user = get_user_model().objects.create_user("fiktiv-import")
        self.other = get_user_model().objects.create_user("anderer-import")
        self.client.force_login(self.user)

    def prepare(self, payload=None):
        return prepare(self.user, self.client.session.session_key, json.dumps(payload or bundle()))[
            0
        ]

    def ready(self, draft):
        initial = review(draft, self.user)
        result = review(draft, self.user, posted_forms(initial))
        self.assertTrue(
            result["ready"],
            [
                (r["form"].errors)
                for key in ["customers", "positions", "appointments"]
                for r in result[key]
            ]
            + result["problems"],
        )
        return draft.confirmation

    def test_bundle_preview_confirmation_atomic_and_replay(self):
        payload = bundle()
        draft = self.prepare(payload)
        self.assertEqual(Customer.objects.count(), 0)
        url = reverse("intake:draft", args=[draft.key])
        self.assertContains(self.client.get(url), "NOCH NICHT GESPEICHERT")
        data = posted_forms(review(draft, self.user))
        self.assertContains(self.client.post(url, data), "Jetzt verbindlich übernehmen")
        self.assertEqual(Customer.objects.count(), 0)
        self.assertEqual(CustomerEvent.objects.count(), 0)
        self.assertEqual(ImportReceipt.objects.count(), 0)
        self.assertContains(self.client.get(reverse("intake:start")), "haarvinci.import")
        # GET verwirft die Bestätigung: jede neue Vorschau muss neu geprüft werden.
        self.ready(draft)
        nonce = draft.confirmation
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(url, {"action": "confirm", "confirmation": nonce})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            (
                Customer.objects.count(),
                ExtensionPosition.objects.count(),
                Appointment.objects.count(),
            ),
            (1, 1, 1),
        )
        person = Customer.objects.get()
        self.assertEqual(str(person.desired_length), "50.5")
        self.assertEqual(ExtensionPosition.objects.get().customer, person)
        self.assertEqual(Appointment.objects.get().customer, person)
        self.assertEqual(CustomerEvent.objects.count(), 3)
        self.assertIsNone(draft.plan)
        self.assertNotIn("customers", draft.payload)
        self.assertEqual(commit(draft, self.user, nonce).pk, ImportReceipt.objects.get().pk)
        self.assertIsNotNone(
            prepare(self.user, self.client.session.session_key, json.dumps(payload))[1]
        )
        payload["customers"][0]["data"]["first_name"] = "Anders"
        with self.assertRaises(ImportProblem):
            prepare(self.user, self.client.session.session_key, json.dumps(payload))

    def test_rejects_wrong_shape_unknown_fields_duplicates_and_links(self):
        payload = bundle()
        invalid = [
            "https://chatgpt.com/share/fiktiv",
            '{"format":1,"format":2}',
            "[]",
            "{}",
            "null",
            "NaN",
            "{",
            "x" * 65537,
        ]
        for change in [
            lambda p: p.update(version=True),
            lambda p: p.update(id=[]),
            lambda p: p["customers"][0]["data"].update(owner="1"),
            lambda p: p["extensions"][0].update(customer_ref=[]),
            lambda p: p["customers"][0]["data"].update(notes={}),
            lambda p: p["appointments"][0]["data"].update(allow_overlap=True),
        ]:
            bad = copy.deepcopy(payload)
            change(bad)
            invalid.append(json.dumps(bad))
        for text in invalid:
            with self.subTest(text=text[:70]), self.assertRaises(ImportProblem):
                parse(text)
        self.assertEqual(
            parse("Hier ist das Paket:\n```json\n" + json.dumps(payload) + "\n```")[0]["version"], 1
        )

    def test_missing_and_invalid_fields_are_editable_without_writes(self):
        payload = bundle()
        payload["customers"][0]["data"] = {"first_name": "Lina"}
        payload["extensions"][0]["data"]["weight_g"] = "-5"
        draft = self.prepare(payload)
        result = review(draft, self.user)
        self.assertIn("last_name", result["customers"][0]["form"].errors)
        self.assertIn("weight_g", result["positions"][0]["form"].errors)
        data = posted_forms(result)
        data.update(
            {
                "c0-field-last_name": "Fiktivblüte",
                "c0-field-email": "lina@example.com",
                "x0-weight_g": "100,25",
            }
        )
        self.assertTrue(review(draft, self.user, data)["ready"])
        self.assertFalse(Customer.objects.exists())
        with self.assertRaises(ImportProblem):
            commit(draft, self.user, "falsch")

    def test_existing_customer_requires_explicit_owner_scoped_selection(self):
        own = Customer.objects.create(
            owner=self.user, first_name="Lina", last_name="Fiktivblüte", email="lina@example.com"
        )
        foreign = Customer.objects.create(
            owner=self.other, first_name="Fremd", last_name="Fiktiv", email="fremd@example.com"
        )
        payload = bundle()
        payload["customers"][0] = {
            "ref": "k1",
            "mode": "existing",
            "hint": "Lina",
            "data": {"natural_color": "Kupfer"},
        }
        draft = self.prepare(payload)
        data = posted_forms(review(draft, self.user))
        self.assertFalse(review(draft, self.user, data)["ready"])
        data["c0-target"] = str(foreign.pk)
        data["c0-apply"] = "on"
        self.assertFalse(review(draft, self.user, data)["ready"])
        data["c0-target"] = str(own.pk)
        self.assertTrue(review(draft, self.user, data)["ready"])
        commit(draft, self.user, draft.confirmation)
        own.refresh_from_db()
        self.assertEqual(own.natural_color, "Kupfer")
        self.assertEqual(own.email, "lina@example.com")
        self.assertEqual(Customer.objects.for_user(self.user).count(), 1)

    def test_concurrent_existing_edit_rejects_whole_bundle(self):
        own = Customer.objects.create(
            owner=self.user, first_name="Lina", last_name="Test", email="lina@example.com"
        )
        payload = bundle()
        payload["customers"][0] = {"ref": "k1", "mode": "existing"}
        draft = self.prepare(payload)
        data = posted_forms(review(draft, self.user))
        data["c0-target"] = str(own.pk)
        self.assertTrue(review(draft, self.user, data)["ready"])
        Customer.objects.filter(pk=own.pk).update(version=2)
        with self.assertRaises(ImportProblem):
            commit(draft, self.user, draft.confirmation)
        self.assertFalse(Appointment.objects.exists())
        self.assertFalse(ExtensionPosition.objects.exists())

    def test_similar_and_duplicate_new_customers_are_blocked(self):
        payload = bundle()
        Customer.objects.create(
            owner=self.user,
            first_name="Lina",
            last_name="Fiktivblüte",
            email="lina.import@example.com",
        )
        draft = self.prepare(payload)
        data = posted_forms(review(draft, self.user))
        self.assertFalse(review(draft, self.user, data)["ready"])
        data["c0-target"] = str(Customer.objects.get().pk)
        self.assertTrue(review(draft, self.user, data)["ready"])
        payload["customers"].append(copy.deepcopy(payload["customers"][0]) | {"ref": "k2"})
        Customer.objects.all().delete()
        draft = self.prepare(payload)
        self.assertFalse(review(draft, self.user, posted_forms(review(draft, self.user)))["ready"])

    def test_appointment_race_rolls_back_customers_extensions_and_history(self):
        draft = self.prepare()
        self.ready(draft)
        from appointments.services import ScheduleConflict

        with (
            patch("intake.services.save_appointment", side_effect=ScheduleConflict([])),
            self.assertRaises(ImportProblem),
        ):
            commit(draft, self.user, draft.confirmation)
        for model in [Customer, ExtensionPosition, CustomerEvent, ImportReceipt]:
            self.assertEqual(model.objects.count(), 0)

    def test_new_matching_customer_between_preview_and_confirm_is_blocked(self):
        draft = self.prepare()
        self.ready(draft)
        Customer.objects.create(
            owner=self.user,
            first_name="Lina",
            last_name="Fiktivblüte",
            email="lina.import@example.com",
        )
        with self.assertRaises(ImportProblem):
            commit(draft, self.user, draft.confirmation)
        self.assertEqual(Customer.objects.count(), 1)
        self.assertFalse(ExtensionPosition.objects.exists())

    def test_duplicates_and_dst_and_overlap_are_rejected(self):
        for mutate in [
            lambda p: p["extensions"].append(copy.deepcopy(p["extensions"][0])),
            lambda p: p["appointments"].append(copy.deepcopy(p["appointments"][0])),
            lambda p: p["appointments"][0]["data"].update(
                day="2027-03-28", begin="02:30", finish="04:00"
            ),
            lambda p: p["appointments"].append(
                {
                    "customer_ref": "k1",
                    "data": p["appointments"][0]["data"] | {"begin": "10:30", "finish": "12:00"},
                }
            ),
        ]:
            payload = bundle()
            mutate(payload)
            draft = self.prepare(payload)
            self.assertFalse(
                review(draft, self.user, posted_forms(review(draft, self.user)))["ready"]
            )

    def test_repeated_confirm_and_changed_import_id_cannot_duplicate(self):
        payload = bundle()
        draft = self.prepare(payload)
        self.ready(draft)
        nonce = draft.confirmation
        commit(draft, self.user, nonce)
        commit(draft, self.user, nonce)
        self.assertEqual(ImportReceipt.objects.count(), 1)
        payload["id"] = str(uuid.uuid4())
        draft = self.prepare(payload)
        self.assertFalse(review(draft, self.user, posted_forms(review(draft, self.user)))["ready"])

    def test_drafts_require_same_login_and_have_expiry(self):
        draft = self.prepare()
        with self.assertRaises(ImportProblem):
            find(draft.key, self.other, self.client.session.session_key)
        with self.assertRaises(ImportProblem):
            find(draft.key, self.user, "andere-sitzung")
        draft.created -= 2000
        with self.assertRaises(ImportProblem):
            find(draft.key, self.user, self.client.session.session_key)
        self.assertEqual(
            self.client.get(reverse("intake:draft", args=[draft.key])).status_code, 410
        )

    def test_native_auth_gate_csrf_and_receipt_owner(self):
        from intake.views import native_prepare

        with patch("django.db.close_old_connections"):
            self.assertNotIn("path", json.loads(native_prepare("", json.dumps(bundle()))))
        self.client.logout()
        self.assertEqual(self.client.get(reverse("intake:start")).status_code, 302)
        self.client.force_login(self.user)
        draft = self.prepare()
        self.ready(draft)
        saved = commit(draft, self.user, draft.confirmation)
        self.client.force_login(self.other)
        self.assertEqual(
            self.client.get(reverse("intake:receipt", args=[saved.pk])).status_code, 404
        )
