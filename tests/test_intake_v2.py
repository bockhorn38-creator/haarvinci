import copy
import json
import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from appointments.models import Appointment
from customers.models import Customer, CustomerEvent
from extensions.models import ExtensionPosition
from intake.models import ImportReceipt
from intake.parser import ImportProblem, parse
from intake.services import DRAFTS, commit, prepare, review
from tests.test_intake import bundle, posted_forms
from treatments.models import Payment, PriceOption, Treatment
from treatments.services import BusinessError


def bundle2():
    result = bundle()
    result["version"] = 2
    result["extensions"][0]["ref"] = "x1"
    result["appointments"][0]["ref"] = "a1"
    result["treatments"] = [
        {
            "ref": "b1",
            "customer_ref": "k1",
            "mode": "new",
            "appointment_ref": "a1",
            "extension_refs": ["x1"],
            "services": ["Fiktive Haarwäsche"],
            "data": {
                "performed_on": result["appointments"][0]["data"]["day"],
                "description": "Weaving fiktiv",
                "status": "planned",
                "rows": 2,
                "price_mode": "weaving",
                "notes": "Aus ChatGPT übernommen, fiktiv.",
            },
        }
    ]
    result["payments"] = [
        {
            "ref": "z1",
            "treatment_ref": "b1",
            "data": {
                "amount": "50,00",
                "booked_on": str(timezone.localdate()),
                "method": "cash",
                "purpose": "deposit",
            },
        },
        {
            "ref": "z2",
            "treatment_ref": "b1",
            "data": {
                "amount": "115,00",
                "booked_on": str(timezone.localdate()),
                "method": "bank",
                "purpose": "final",
            },
        },
    ]
    return result


def posted_all(result):
    data = posted_forms(result)
    for key in ["treatments", "payments"]:
        for entry in result[key]:
            form = entry["form"]
            for name, field in form.fields.items():
                values = form.data.get(form.add_prefix(name), "")
                if isinstance(field, __import__("django").forms.ModelMultipleChoiceField):
                    values = (
                        form.data.getlist(form.add_prefix(name))
                        if hasattr(form.data, "getlist")
                        else values
                        if isinstance(values, list)
                        else [values]
                        if values
                        else []
                    )
                    data.setlist(form.add_prefix(name), values)
                else:
                    data[form.add_prefix(name)] = values
    return data


@override_settings(DEBUG=True, AXES_ENABLED=False, SECURE_SSL_REDIRECT=False)
class ImportV2Tests(TestCase):
    def setUp(self):
        DRAFTS.clear()
        self.user = get_user_model().objects.create_user("import2-fiktiv")
        self.other = get_user_model().objects.create_user("import2-fremd")
        self.client.force_login(self.user)
        self.tariff = PriceOption.objects.create(
            owner=self.user, name="Fiktive 2 Reihen", category="weaving", rows=2, price="145.00"
        )
        self.wash = PriceOption.objects.create(
            owner=self.user, name="Fiktive Haarwäsche", category="service", price="20.00"
        )

    def prepare(self, payload=None):
        return prepare(
            self.user, self.client.session.session_key, json.dumps(payload or bundle2())
        )[0]

    def ready(self, draft, data=None):
        result = review(draft, self.user, data or posted_all(review(draft, self.user)))
        self.assertTrue(
            result["ready"],
            result["problems"]
            + [
                (entry["form"].errors)
                for key in ["customers", "positions", "appointments", "treatments", "payments"]
                for entry in result[key]
            ],
        )
        return result

    def test_complete_linked_bundle_waits_for_confirmation_then_saves_once(self):
        payload = bundle2()
        draft = self.prepare(payload)
        self.ready(draft)
        self.assertFalse(Customer.objects.exists())
        self.assertFalse(Treatment.objects.exists())
        self.assertFalse(Payment.objects.exists())
        url = reverse("intake:draft", args=[draft.key])
        # Render the actual final overview, including money and treatment references.
        result = review(draft, self.user, posted_all(review(draft, self.user)))
        self.assertTrue(result["ready"])
        nonce = draft.confirmation
        response = self.client.post(url, {"action": "confirm", "confirmation": nonce})
        self.assertEqual(response.status_code, 302)
        treatment = Treatment.objects.get()
        self.assertEqual(treatment.customer, Customer.objects.get())
        self.assertEqual(treatment.appointment, Appointment.objects.get())
        self.assertEqual(treatment.extension_links.get().position, ExtensionPosition.objects.get())
        self.assertEqual(
            (treatment.total, treatment.net_paid, treatment.outstanding),
            (Decimal("165.00"), Decimal("165.00"), 0),
        )
        self.assertEqual(Payment.objects.count(), 2)
        self.assertEqual(ImportReceipt.objects.get().counts["treatments"], 1)
        self.assertEqual(ImportReceipt.objects.get().counts["payments"], 2)
        self.assertIsNotNone(
            prepare(self.user, self.client.session.session_key, json.dumps(payload))[1]
        )
        commit(draft, self.user, nonce)
        self.assertEqual(Payment.objects.count(), 2)

    def test_new_material_reference_price_is_reused_without_retyping(self):
        payload = bundle2()
        payload["extensions"][0]["data"]["sale_price"] = "100,00"
        payload["treatments"][0]["data"]["charge_extensions"] = True
        draft = self.prepare(payload)
        self.ready(draft)
        commit(draft, self.user, draft.confirmation)
        self.assertEqual(Treatment.objects.get().total, Decimal("265.00"))
        self.assertEqual(Treatment.objects.get().outstanding, 100)

    def test_multiple_treatments_and_payment_references_are_distinct(self):
        payload = bundle2()
        payload["treatments"].append(
            {
                "ref": "b2",
                "customer_ref": "k1",
                "mode": "new",
                "data": {
                    "performed_on": str(timezone.localdate()),
                    "description": "Individuelle Pflege",
                    "status": "completed",
                    "price_mode": "individual",
                    "custom_price": "25,50",
                },
            }
        )
        payload["payments"].append(
            {
                "ref": "z3",
                "treatment_ref": "b2",
                "data": {
                    "amount": "25,50",
                    "booked_on": str(timezone.localdate()),
                    "method": "cash",
                    "purpose": "final",
                },
            }
        )
        draft = self.prepare(payload)
        self.ready(draft)
        commit(draft, self.user, draft.confirmation)
        self.assertEqual(Treatment.objects.count(), 2)
        self.assertEqual(Payment.objects.count(), 3)
        self.assertEqual(
            Treatment.objects.get(description="Individuelle Pflege").net_paid, Decimal("25.50")
        )

    def existing_payload(self, treatment):
        return {
            "format": "haarvinci.import",
            "version": 2,
            "id": str(uuid.uuid4()),
            "customers": [{"ref": "k1", "mode": "existing", "hint": "Lina"}],
            "treatments": [
                {
                    "ref": "b1",
                    "customer_ref": "k1",
                    "mode": "existing",
                    "hint": "Vorgang manuell auswählen",
                }
            ],
            "payments": [
                {
                    "ref": "z1",
                    "treatment_ref": "b1",
                    "data": {
                        "amount": "10",
                        "booked_on": str(timezone.localdate()),
                        "method": "cash",
                        "purpose": "partial",
                        "notes": "Weitere fiktive Teilzahlung",
                    },
                }
            ],
        }

    def existing(self):
        draft = self.prepare()
        self.ready(draft)
        commit(draft, self.user, draft.confirmation)
        treatment = Treatment.objects.get()
        # Keep a partial payment only to make room for another actual payment.
        Payment.objects.filter(purpose="final").delete()
        return treatment

    def test_existing_customer_and_treatment_need_explicit_consistent_selection(self):
        treatment = self.existing()
        draft = self.prepare(self.existing_payload(treatment))
        initial = review(draft, self.user)
        data = posted_all(initial)
        self.assertFalse(review(draft, self.user, data)["ready"])
        data.update({"c0-target": str(treatment.customer_id), "t0-target": str(treatment.pk)})
        self.ready(draft, data)
        commit(draft, self.user, draft.confirmation)
        self.assertEqual(Treatment.objects.count(), 1)
        self.assertEqual(treatment.net_paid, 60)

    def test_existing_financial_version_changes_reject_entire_confirmation(self):
        treatment = self.existing()
        payload = self.existing_payload(treatment)
        draft = self.prepare(payload)
        data = posted_all(review(draft, self.user))
        data.update({"c0-target": str(treatment.customer_id), "t0-target": str(treatment.pk)})
        self.ready(draft, data)
        Treatment.objects.filter(pk=treatment.pk).update(version=treatment.version + 1)
        with self.assertRaises(ImportProblem):
            commit(draft, self.user, draft.confirmation)
        self.assertEqual(treatment.net_paid, 50)

    def test_multiple_payments_must_fit_total_and_no_duplicate_money_lines(self):
        for mutate in [
            lambda p: p["payments"][1]["data"].update(amount="116"),
            lambda p: p["payments"].append(copy.deepcopy(p["payments"][0]) | {"ref": "z3"}),
        ]:
            payload = bundle2()
            mutate(payload)
            draft = self.prepare(payload)
            self.assertFalse(
                review(draft, self.user, posted_all(review(draft, self.user)))["ready"]
            )
        self.assertFalse(Customer.objects.exists())

    def test_refund_in_same_bundle_is_linked_to_correct_original(self):
        payload = bundle2()
        payload["payments"] = payload["payments"][:1] + [
            {
                "ref": "r1",
                "treatment_ref": "b1",
                "refund_of": "z1",
                "data": {
                    "kind": "refund",
                    "amount": "20",
                    "booked_on": str(timezone.localdate()),
                    "method": "cash",
                    "notes": "Fiktive echte Rückgabe",
                },
            }
        ]
        draft = self.prepare(payload)
        self.ready(draft)
        commit(draft, self.user, draft.confirmation)
        item = Treatment.objects.get()
        self.assertEqual(item.net_paid, 30)
        refund = Payment.objects.get(kind="refund")
        self.assertEqual(refund.original, Payment.objects.get(kind="receipt"))

    def test_catalog_race_rolls_back_customer_extensions_appointments_and_payments(self):
        draft = self.prepare()
        self.ready(draft)
        self.tariff.price = 999
        self.tariff.version += 1
        self.tariff.save()
        with self.assertRaises(BusinessError):
            commit(draft, self.user, draft.confirmation)
        for model in [
            Customer,
            ExtensionPosition,
            Appointment,
            Treatment,
            Payment,
            ImportReceipt,
            CustomerEvent,
        ]:
            self.assertFalse(model.objects.exists(), model)

    def test_v2_invalid_refs_shapes_unknown_fields_and_cross_links_rejected(self):
        mutations = [
            lambda p: p["treatments"][0].update(appointment_ref=[]),
            lambda p: p["payments"][0].update(refund_of=[]),
            lambda p: p["treatments"][0].update(customer_ref="fremd"),
            lambda p: p["treatments"][0].update(extension_refs=["a1"]),
            lambda p: p["payments"][0].update(treatment_ref="unbekannt"),
            lambda p: p["treatments"][0]["data"].update(owner="1"),
            lambda p: p["treatments"][0]["data"].update(charge_extensions="vielleicht"),
            lambda p: p["payments"][0]["data"].update(booking_key=str(uuid.uuid4())),
            lambda p: p["payments"][0].update(ref="b1"),
        ]
        for mutate in mutations:
            payload = bundle2()
            mutate(payload)
            with self.assertRaises(ImportProblem):
                parse(json.dumps(payload))

    def test_version_one_still_accepted_but_cannot_smuggle_financial_fields(self):
        payload = bundle()
        self.assertEqual(parse(json.dumps(payload))[0]["version"], 1)
        payload["payments"] = []
        with self.assertRaises(ImportProblem):
            parse(json.dumps(payload))

    def test_missing_money_fields_and_rows_show_errors_without_any_write(self):
        payload = bundle2()
        payload["payments"][0]["data"].pop("amount")
        payload["treatments"][0]["data"].pop("rows")
        draft = self.prepare(payload)
        result = review(draft, self.user)
        self.assertIn("rows", result["treatments"][0]["form"].errors)
        self.assertIn("amount", result["payments"][0]["form"].errors)
        self.assertFalse(Treatment.objects.exists())
