import copy
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from appointments.device_native import DeviceController
from appointments.device_sync import DeviceError, sync_all
from appointments.models import (
    Appointment,
    AppointmentType,
    DeviceCalendarConnection,
    DeviceEventBinding,
    DevicePrivateBusy,
)
from customers.models import Customer, CustomerEvent


class Provider:
    def __init__(self):
        self.rows = {}
        self.writes = []
        self.readable = self.writable = True
        self.fail = None
        self.blocks = []

    def permissions(self):
        return {"read": self.readable, "write": self.writable}

    def calendars(self, role):
        return [
            {"id": "1", "fingerprint": "a" * 64, "label": "Fiktiv geschäftlich"},
            {"id": "2", "fingerprint": "b" * 64, "label": "Fiktiv privat"},
        ]

    def read(self, connection, binding):
        return copy.deepcopy(self.rows.get(binding.marker.hex, {"status": "missing"}))

    def write(self, connection, binding, action, revision, payload):
        self.writes.append((action, binding.marker.hex, copy.deepcopy(payload)))
        if self.fail:
            return self.fail
        if action == "delete":
            self.rows.pop(binding.marker.hex, None)
            return {"status": "deleted"}
        row = {
            "status": "found",
            "event": payload,
            "id": "33",
            "revision": str(len(self.writes)),
            "marker_present": True,
        }
        self.rows[binding.marker.hex] = row
        return copy.deepcopy(row)

    def instances(self, connection, start, end, skipped):
        return copy.deepcopy(self.blocks)


@override_settings(AXES_ENABLED=False)
class DeviceCalendarTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("fiktiv-device")
        self.other = get_user_model().objects.create_user("fremd-device")
        self.customer = Customer.objects.create(
            owner=self.user, first_name="Lina", last_name="Fiktiv", email="lina@example.com"
        )
        self.connection = DeviceCalendarConnection.objects.create(
            owner=self.user, role="business", calendar_id="1", fingerprint="a" * 64
        )
        start = timezone.now() + timedelta(days=1)
        self.item = Appointment.objects.create(
            owner=self.user,
            customer=self.customer,
            appointment_type=AppointmentType.objects.first(),
            start_at=start,
            end_at=start + timedelta(hours=1),
        )
        self.provider = Provider()

    def sync(self):
        sync_all(self.provider, self.user)
        self.item.refresh_from_db()
        return DeviceEventBinding.objects.get(appointment=self.item)

    def test_offline_intent_repeated_sync_update_and_cancel(self):
        binding = self.sync()
        self.assertEqual(self.item.sync_state, "synced")
        self.sync()
        self.assertEqual(len(self.provider.writes), 1)
        self.item.notes, self.item.version = "Lokal geändert", 2
        self.item.save()
        self.sync()
        self.assertEqual(self.provider.writes[-1][0], "update")
        self.item.status, self.item.version = "cancelled", 3
        self.item.save()
        self.sync()
        self.assertEqual(self.provider.writes[-1][0], "delete")
        self.sync()
        self.assertEqual(self.item.sync_state, "synced")
        self.assertEqual(len(self.provider.writes), 3)
        self.item.status, self.item.version = "planned", 4
        self.item.save()
        changed = self.sync()
        self.assertNotEqual(binding.marker, changed.marker)
        self.assertEqual(self.provider.writes[-1][0], "insert")

    def test_remote_only_change_is_audited_but_two_sided_change_requires_choice(self):
        binding = self.sync()
        self.provider.rows[binding.marker.hex]["event"]["notes"] = "Am Gerät geändert"
        self.provider.rows[binding.marker.hex]["revision"] = "r2"
        self.sync()
        self.assertEqual(self.item.notes, "Am Gerät geändert")
        self.assertEqual(CustomerEvent.objects.count(), 1)
        self.item.notes, self.item.version = "Lokal", self.item.version + 1
        self.item.save()
        self.provider.rows[binding.marker.hex]["event"]["notes"] = "Andere Änderung"
        self.provider.rows[binding.marker.hex]["revision"] = "r3"
        self.sync()
        self.assertEqual(self.item.sync_state, "conflict")
        self.assertEqual(self.item.notes, "Lokal")
        self.assertEqual(len(self.provider.writes), 1)
        controller = DeviceController(self.provider)
        data = {
            "appointment": str(self.item.pk),
            "version": str(self.item.version),
            "proof": self.item.conflict_token,
            "choice": "remote",
        }
        controller.resolve(self.user, data)
        self.item.refresh_from_db()
        self.assertEqual(self.item.notes, "Andere Änderung")
        with self.assertRaises(DeviceError):
            controller.resolve(self.user, data)

    def test_missing_identity_duplicate_moved_and_recurring_never_recreate(self):
        binding = self.sync()
        for status in ["missing", "identity", "duplicate", "moved", "recurring"]:
            self.provider.rows[binding.marker.hex] = {"status": status}
            self.sync()
            self.assertEqual(self.item.sync_state, "conflict")
            self.assertEqual(len(self.provider.writes), 1)
        self.assertFalse(CustomerEvent.objects.exists())

    def test_ambiguous_insert_retries_lookup_without_second_insert(self):
        self.provider.fail = {"status": "unavailable"}
        self.sync()
        self.provider.fail = None
        self.sync()
        self.assertEqual(len(self.provider.writes), 1)
        self.assertEqual(self.item.sync_state, "conflict")

    def test_definite_permission_failure_can_retry_after_permission_restored(self):
        self.provider.fail = {"status": "permission", "definite": True}
        self.sync()
        self.provider.fail = None
        self.sync()
        self.assertEqual(self.item.sync_state, "synced")
        self.assertEqual(len(self.provider.writes), 2)

    def test_cas_race_does_not_claim_written_state(self):
        binding = self.sync()
        self.item.notes, self.item.version = "Neue lokale Notiz", 2
        self.item.save()
        self.provider.fail = {"status": "race", "definite": True}
        self.provider.rows[binding.marker.hex]["revision"] = "geändert"
        self.sync()
        self.assertEqual(self.item.sync_state, "conflict")
        self.assertEqual(self.item.remote_conflict["revision"], "geändert")

    def test_private_data_storage_only_times_and_permission_revocation(self):
        self.connection.role = "private"
        self.connection.save()
        self.provider.blocks = [
            {
                "start": self.item.start_at.isoformat(),
                "end": self.item.end_at.isoformat(),
                "title": "Darf nie gespeichert werden",
                "notes": "Vertraulich",
            }
        ]
        self.sync_private()
        self.assertEqual(DevicePrivateBusy.objects.count(), 1)
        self.assertEqual(
            {field.name for field in DevicePrivateBusy._meta.fields},
            {"id", "connection", "start_at", "end_at"},
        )
        self.assertFalse(self.provider.writes)
        self.provider.readable = False
        self.sync_private()
        self.assertFalse(DevicePrivateBusy.objects.exists())
        self.connection.refresh_from_db()
        self.assertEqual(self.connection.state, "permission")

    def sync_private(self):
        sync_all(self.provider, self.user)

    def test_selection_prevents_same_calendar_and_bound_calendar_change(self):
        controller = DeviceController(self.provider)
        with self.assertRaises(DeviceError):
            controller.choose(self.user, "private", "1")
        controller.choose(self.user, "private", "2")
        self.sync()
        controller.disconnect(self.user, "private")
        with self.assertRaises(DeviceError):
            controller.choose(self.user, "business", "2")
        self.provider.readable = False
        with self.assertRaises(DeviceError):
            controller.choices(self.user, "business")

    def test_missing_decision_can_pause_but_never_guess_a_new_event(self):
        binding = self.sync()
        self.provider.rows.pop(binding.marker.hex)
        self.sync()
        DeviceController(self.provider).resolve(
            self.user,
            {
                "appointment": str(self.item.pk),
                "version": self.item.version,
                "proof": self.item.conflict_token,
                "choice": "local",
            },
        )
        binding.refresh_from_db()
        self.assertTrue(binding.paused)
        self.sync()
        self.assertEqual(self.item.sync_state, "local")
        self.assertEqual(len(self.provider.writes), 1)

    @override_settings(SECURE_SSL_REDIRECT=False)
    def test_foreign_provider_event_opens_read_only_for_its_owner(self):
        from django.urls import reverse

        from appointments.models import DeviceBusinessEvent

        event = DeviceBusinessEvent.objects.create(
            connection=self.connection,
            occurrence_key="fiktiv:1",
            title="Fiktive fremde Belegung",
            start_at=self.item.start_at,
            end_at=self.item.end_at,
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse("appointments:external", args=[event.pk]))
        self.assertContains(response, "Fiktive fremde Belegung")
        self.assertContains(response, "wird hier nicht verändert")
        self.assertNotContains(response, "Bearbeiten / verschieben")
        self.client.force_login(self.other)
        self.assertEqual(
            self.client.get(reverse("appointments:external", args=[event.pk])).status_code, 404
        )

    def test_customer_rename_is_also_a_local_calendar_change(self):
        binding = self.sync()
        self.customer.first_name = "Nele"
        self.customer.save()
        self.provider.rows[binding.marker.hex]["event"]["title"] = "Unabhängiger Geräte-Titel"
        self.provider.rows[binding.marker.hex]["revision"] = "r-neu"
        self.sync()
        self.assertEqual(self.item.sync_state, "conflict")
        self.assertEqual(len(self.provider.writes), 1)

    def test_own_event_converted_to_all_day_is_not_silently_imported(self):
        binding = self.sync()
        self.provider.rows[binding.marker.hex]["event"]["all_day"] = True
        self.sync()
        self.assertEqual(self.item.sync_state, "conflict")
        self.assertFalse(self.item.remote_conflict["manageable"])
        self.assertEqual(len(self.provider.writes), 1)

    def test_another_owner_cannot_resolve_or_sync_this_appointment(self):
        binding = self.sync()
        self.provider.rows[binding.marker.hex] = {"status": "missing"}
        sync_all(self.provider, self.other)
        self.assertEqual(len(self.provider.writes), 1)
        with self.assertRaises(Appointment.DoesNotExist):
            DeviceController(self.provider).resolve(self.other, {"appointment": self.item.pk})
