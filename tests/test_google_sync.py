import copy
import time
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import serializers
from django.test import TestCase, override_settings
from django.utils import timezone

from appointments.google_api import SCOPES, GoogleCalendarAPI, GoogleError, NoRedirect
from appointments.models import (
    Appointment,
    AppointmentType,
    CalendarConnection,
    CalendarSettings,
    PrivateBusy,
    RemoteBusinessEvent,
)
from appointments.native import GoogleController, vault_key
from appointments.sync import event_id, payload, resolve_conflict, sync_connection
from customers.models import Customer


class FakeGoogle:
    def __init__(self):
        self.records, self.writes = {}, []
        self.failure = None
        self.lose_insert_response = False
        self.patch_race = False

    def calendars(self):
        return [
            {
                "id": "business@example.com",
                "summary": "Fiktiver Geschäftskalender",
                "accessRole": "owner",
            }
        ]

    def events(self, calendar, start, end):
        if self.failure:
            raise GoogleError(self.failure)
        return copy.deepcopy(list(self.records.values())), "Europe/Berlin"

    def event(self, calendar, remote_id, *, method="GET", data=None, etag=None):
        if remote_id not in self.records:
            raise GoogleError(404)
        current = self.records[remote_id]
        if method == "GET":
            return copy.deepcopy(current)
        if self.patch_race:
            self.patch_race = False
            current["description"] = "Gleichzeitig bei Google geändert"
            current["etag"] = "race-etag"
            raise GoogleError(412)
        if etag != current.get("etag"):
            raise GoogleError(412)
        self.writes.append((method, remote_id))
        if method == "DELETE":
            self.records[remote_id] = {
                "id": remote_id,
                "status": "cancelled",
                "etag": "deleted-etag",
            }
            return {}
        current.update(copy.deepcopy(data))
        current["etag"] = current["etag"] + "-new"
        return copy.deepcopy(current)

    def insert(self, calendar, data):
        if data["id"] in self.records:
            raise GoogleError(409)
        self.writes.append(("POST", data["id"]))
        self.records[data["id"]] = copy.deepcopy(data) | {
            "status": "confirmed",
            "etag": "created-etag",
        }
        if self.lose_insert_response:
            self.lose_insert_response = False
            raise GoogleError(0)
        return copy.deepcopy(self.records[data["id"]])

    def busy(self, calendar, start, end):
        if self.failure:
            raise GoogleError(self.failure)
        return {
            "calendars": {
                calendar: {
                    "busy": [
                        {
                            "start": "2026-11-05T10:00:00+01:00",
                            "end": "2026-11-05T11:00:00+01:00",
                            "summary": "Privater Titel darf nie gespeichert werden",
                            "attendees": ["private@example.com"],
                        }
                    ]
                }
            }
        }


class MemoryVault:
    def __init__(self):
        self.records = {}

    def load(self, key):
        return copy.deepcopy(self.records.get(key, {}))

    def save(self, key, data):
        self.records[key] = copy.deepcopy(data)


@override_settings(AXES_ENABLED=False, SECURE_SSL_REDIRECT=False)
class GoogleSyncTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user("google-fiktiv")
        cls.customer = Customer.objects.create(
            owner=cls.owner, first_name="Mila", last_name="Testgarten", email="mila@example.com"
        )
        cls.kind = AppointmentType.objects.filter(owner__isnull=True).first()

    def setUp(self):
        self.api = FakeGoogle()
        self.config = CalendarSettings.objects.create(
            owner=self.owner, broker_url="https://auth.example.com"
        )
        self.connection = CalendarConnection.objects.create(
            owner=self.owner, role="business", calendar_id="business@example.com", state="connected"
        )
        self.item = Appointment.objects.create(
            owner=self.owner,
            customer=self.customer,
            appointment_type=self.kind,
            start_at=timezone.now() + timedelta(days=1),
            end_at=timezone.now() + timedelta(days=1, hours=1),
            notes="Fiktive Ausgangsnotiz",
        )

    def sync(self):
        sync_connection(self.connection, self.api)
        self.item.refresh_from_db()

    def test_insert_is_idempotent_and_only_owned_event_is_written(self):
        self.api.records["foreign"] = {
            "id": "foreign",
            "summary": "Fremder Geschäftstermin",
            "start": {"date": "2026-11-01"},
            "end": {"date": "2026-11-02"},
            "etag": "foreign-etag",
        }
        self.sync()
        self.sync()
        self.assertEqual(self.api.writes, [("POST", event_id(self.item))])
        self.assertEqual(self.item.sync_state, "synced")
        self.assertEqual(RemoteBusinessEvent.objects.get().title, "Fremder Geschäftstermin")
        self.assertEqual(self.api.records["foreign"]["etag"], "foreign-etag")

    def test_lost_insert_response_never_produces_duplicate(self):
        self.api.lose_insert_response = True
        with self.assertRaises(GoogleError):
            self.sync()
        self.sync()
        self.assertEqual(len(self.api.records), 1)
        self.assertEqual(len(self.api.writes), 1)
        self.assertEqual(self.item.google_event_id, event_id(self.item))

    def test_local_change_patch_uses_etag_and_cancellation_only_deletes_owned_event(self):
        self.sync()
        self.item.notes = "Lokal geändert"
        self.item.version += 1
        self.item.save()
        self.sync()
        self.assertEqual(self.api.records[event_id(self.item)]["description"], "Lokal geändert")
        self.item.status, self.item.version = "cancelled", self.item.version + 1
        self.item.save()
        self.sync()
        self.assertEqual(self.api.records[event_id(self.item)]["status"], "cancelled")
        self.assertEqual([method for method, _ in self.api.writes], ["POST", "PATCH", "DELETE"])

    def test_google_move_notes_and_deletion_are_received_and_audited(self):
        self.sync()
        remote = self.api.records[event_id(self.item)]
        remote["description"], remote["summary"], remote["etag"] = (
            "In Google geändert",
            "Anderer Google-Titel",
            "moved-etag",
        )
        remote["start"]["dateTime"] = (self.item.start_at + timedelta(hours=2)).isoformat()
        remote["end"]["dateTime"] = (self.item.end_at + timedelta(hours=2)).isoformat()
        self.sync()
        self.assertEqual(self.item.notes, "In Google geändert")
        self.assertEqual(self.item.google_title, "Anderer Google-Titel")
        self.assertTrue(self.customer.events.filter(kind="appointment_updated").exists())
        self.api.records[event_id(self.item)] = {
            "id": event_id(self.item),
            "status": "cancelled",
            "etag": "deleted-etag",
        }
        self.sync()
        self.assertEqual(self.item.status, "cancelled")
        self.assertTrue(self.customer.events.filter(kind="appointment_cancelled").exists())

    def conflict(self):
        self.sync()
        self.item.notes, self.item.version = "Lokaler neuer Stand", 2
        self.item.save()
        remote = self.api.records[event_id(self.item)]
        remote["description"], remote["etag"] = "Google neuer Stand", "remote-etag"
        self.sync()
        self.assertEqual(self.item.sync_state, "conflict")
        self.assertEqual(self.item.notes, "Lokaler neuer Stand")
        self.assertEqual(self.item.remote_conflict["notes"], "Google neuer Stand")
        self.assertEqual(len(self.api.writes), 1)

    def test_conflict_never_silently_overwrites_and_remote_choice_is_explicit(self):
        self.conflict()
        resolve_conflict(
            user=self.owner,
            appointment_id=self.item.pk,
            version=self.item.version,
            choice="remote",
            api=self.api,
            connection=self.connection,
        )
        self.item.refresh_from_db()
        self.assertEqual(self.item.notes, "Google neuer Stand")
        self.assertEqual(self.item.sync_state, "synced")

    def test_local_conflict_choice_pushes_using_latest_etag(self):
        self.conflict()
        resolve_conflict(
            user=self.owner,
            appointment_id=self.item.pk,
            version=self.item.version,
            choice="local",
            api=self.api,
            connection=self.connection,
        )
        self.item.refresh_from_db()
        self.assertEqual(
            self.api.records[event_id(self.item)]["description"], "Lokaler neuer Stand"
        )
        self.assertEqual(self.item.sync_state, "synced")

    def test_stale_conflict_decision_is_rejected(self):
        self.conflict()
        self.api.records[event_id(self.item)]["etag"] = "changed-again"
        with self.assertRaises(GoogleError):
            resolve_conflict(
                user=self.owner,
                appointment_id=self.item.pk,
                version=self.item.version,
                choice="local",
                api=self.api,
                connection=self.connection,
            )
        self.assertEqual(len(self.api.writes), 1)

    def test_remote_delete_with_local_change_requires_choice_and_new_generation(self):
        self.sync()
        old_id = event_id(self.item)
        self.item.notes, self.item.version = "Lokal behalten", 2
        self.item.save()
        self.api.records[old_id] = {"id": old_id, "status": "cancelled", "etag": "deleted-etag"}
        self.sync()
        self.assertEqual(self.item.sync_state, "conflict")
        resolve_conflict(
            user=self.owner,
            appointment_id=self.item.pk,
            version=2,
            choice="local",
            api=self.api,
            connection=self.connection,
        )
        self.item.refresh_from_db()
        self.assertEqual(self.item.google_generation, 1)
        self.assertNotEqual(event_id(self.item), old_id)
        self.assertEqual(self.api.records[old_id]["status"], "cancelled")
        self.assertEqual(self.item.sync_state, "synced")

    def test_concurrent_google_write_412_becomes_visible_conflict(self):
        self.sync()
        self.item.notes, self.item.version = "Lokal später", 2
        self.item.save()
        self.api.patch_race = True
        self.sync()
        self.assertEqual(self.item.sync_state, "conflict")
        self.assertEqual(self.item.notes, "Lokal später")
        self.assertEqual(self.item.remote_conflict["notes"], "Gleichzeitig bei Google geändert")

    def test_foreign_id_collision_is_never_adopted_or_changed(self):
        self.api.records[event_id(self.item)] = payload(self.item, self.config) | {
            "etag": "foreign"
        }
        self.api.records[event_id(self.item)]["extendedProperties"] = {
            "private": {"haarvinciInstall": "another-install"}
        }
        self.sync()
        self.assertEqual(self.item.sync_state, "conflict")
        self.assertFalse(self.item.remote_conflict["manageable"])
        self.assertEqual(self.api.writes, [])

    def test_private_sync_persists_only_busy_times(self):
        self.connection.delete()
        private = CalendarConnection.objects.create(
            owner=self.owner, role="private", calendar_id="private@example.com"
        )
        sync_connection(private, self.api)
        block = PrivateBusy.objects.get()
        self.assertEqual(block.start_at, datetime(2026, 11, 5, 9, tzinfo=UTC))
        serialized = serializers.serialize("json", PrivateBusy.objects.all())
        self.assertNotIn("Privater Titel", serialized)
        self.assertNotIn("attendees", serialized)
        self.assertNotIn("private@example.com", serialized)
        self.assertEqual(self.api.writes, [])
        self.assertEqual(RemoteBusinessEvent.objects.count(), 0)

    def test_offline_preserves_cached_times_and_local_outbox(self):
        vault = MemoryVault()
        vault.save(
            vault_key(self.connection),
            {
                "broker": self.config.broker_url,
                "token": {"access_token": "fiktiver-token", "expires_at": time.time() + 3600},
            },
        )
        self.item.sync_state = "pending"
        self.item.save()
        RemoteBusinessEvent.objects.create(
            connection=self.connection,
            remote_id="old",
            title="Vorheriger Cache",
            start_at=self.item.start_at,
            end_at=self.item.end_at,
        )
        self.api.failure = 503
        controller = GoogleController(vault, api_factory=lambda token, role: self.api)
        controller.sync(self.owner)
        self.connection.refresh_from_db()
        self.item.refresh_from_db()
        self.assertEqual(self.connection.state, "error")
        self.assertEqual(self.item.sync_state, "pending")
        self.assertEqual(RemoteBusinessEvent.objects.get().title, "Vorheriger Cache")

    def test_connection_scopes_and_client_prevent_private_event_writes(self):
        self.assertNotIn("https://www.googleapis.com/auth/calendar.events", SCOPES["private"])
        api = GoogleCalendarAPI("fiktiver-token", "private")
        for call in [
            lambda: api.events("private", timezone.now(), timezone.now()),
            lambda: api.event("private", "x", method="DELETE"),
            lambda: api.insert("private", {}),
        ]:
            with self.assertRaises(GoogleError):
                call()
        self.assertIsNone(NoRedirect().redirect_request(None, None, None, None, None, None))

    def test_http_events_pagination_is_complete(self):
        api = GoogleCalendarAPI("fiktiver-token", "business")
        with patch.object(
            api,
            "call",
            side_effect=[
                {"items": [{"id": "first"}], "nextPageToken": "next"},
                {"items": [{"id": "second"}], "timeZone": "Europe/Berlin"},
            ],
        ) as call:
            records, zone = api.events("business@example.com", timezone.now(), timezone.now())
        self.assertEqual([row["id"] for row in records], ["first", "second"])
        self.assertEqual(call.call_args.kwargs["params"]["pageToken"], "next")
        self.assertEqual(zone, "Europe/Berlin")

    def test_inflight_local_edit_is_not_marked_synced_or_overwritten(self):
        original_insert = self.api.insert

        def insert_and_edit(calendar, data):
            result = original_insert(calendar, data)
            Appointment.objects.filter(pk=self.item.pk).update(
                notes="Während Anfrage lokal geändert", version=2
            )
            return result

        self.api.insert = insert_and_edit
        self.sync()
        self.assertEqual(self.item.notes, "Während Anfrage lokal geändert")
        self.assertEqual(self.item.sync_state, "pending")
        self.assertEqual(self.item.last_synced_version, 1)

    def test_controller_tokens_stay_outside_database_and_refresh_is_device_bound(self):
        vault = MemoryVault()
        vault.save(
            vault_key(self.connection),
            {
                "broker": self.config.broker_url,
                "device_id": "fiktives-gerät",
                "device_key": "geheimer-fiktiver-geraeteschluessel",
                "token": {
                    "access_token": "alter-fiktiver-token",
                    "refresh_token": "fiktiver-refresh-token",
                    "expires_at": time.time() - 1,
                },
            },
        )

        def mock_http(url, **kwargs):
            return {
                "token": {"access_token": "neuer-fiktiver-token", "expires_at": time.time() + 3600}
            }

        controller = GoogleController(vault, http=mock_http)
        api = controller.api(self.connection)
        self.assertEqual(api.token, "neuer-fiktiver-token")
        self.assertEqual(
            vault.load(vault_key(self.connection))["token"]["refresh_token"],
            "fiktiver-refresh-token",
        )
        self.assertNotIn(
            "fiktiver-token", serializers.serialize("json", CalendarConnection.objects.all())
        )

    def test_lost_insert_followed_by_google_edit_becomes_conflict(self):
        self.api.lose_insert_response = True
        with self.assertRaises(GoogleError):
            self.sync()
        self.api.records[event_id(self.item)]["description"] = (
            "Bei Google nach dem unklaren Insert geändert"
        )
        self.sync()
        self.assertEqual(self.item.sync_state, "conflict")
        self.assertEqual(self.item.notes, "Fiktive Ausgangsnotiz")
        self.assertEqual(len(self.api.writes), 1)

    def test_native_controller_handoff_chooses_calendar_without_database_tokens(self):
        vault = MemoryVault()

        def http(url, **kwargs):
            if url.endswith("/mobil/start/"):
                self.assertEqual(kwargs["data"]["role"], "business")
                return {
                    "id": "fiktive-handoff-id",
                    "authorization_url": "https://accounts.google.com/o/oauth2/auth?state=fiktiv",
                }
            return {
                "token": {
                    "access_token": "nur-im-vault-fiktiv",
                    "refresh_token": "nur-im-vault-refresh",
                    "expires_at": time.time() + 3600,
                },
                "device_id": "fiktives-gerät",
            }

        controller = GoogleController(vault, api_factory=lambda token, role: self.api, http=http)
        result = controller.begin(self.owner, "business")
        self.assertTrue(result["browser_url"].startswith("https://accounts.google.com/"))
        self.connection.refresh_from_db()
        self.assertEqual(self.connection.state, "pending")
        result = controller.finish(self.owner)
        self.assertEqual(result["calendars"][0]["id"], "business@example.com")
        controller.choose(self.owner, "business", "business@example.com")
        self.connection.refresh_from_db()
        self.assertEqual(self.connection.state, "connected")
        self.assertIsNotNone(self.connection.last_synced_at)
        self.assertNotIn(
            "nur-im-vault", serializers.serialize("json", CalendarConnection.objects.all())
        )

    def test_native_pending_is_not_presented_as_connected(self):
        vault = MemoryVault()
        self.connection.state = "pending"
        self.connection.save()
        vault.save(
            vault_key(self.connection),
            {
                "broker": self.config.broker_url,
                "handoff_id": "fiktiv",
                "verifier": "fiktiv",
                "device_key": "fiktiv",
                "pending_since": time.time(),
            },
        )

        def pending_http(url, **kwargs):
            return {"status": "pending"}

        GoogleController(vault, http=pending_http).finish(self.owner)
        self.connection.refresh_from_db()
        self.assertEqual(self.connection.state, "pending")
        self.assertIsNone(self.connection.last_synced_at)

    def test_broker_address_change_cannot_receive_existing_credentials(self):
        vault = MemoryVault()
        vault.save(
            vault_key(self.connection),
            {"broker": "https://old.example.com", "token": {"access_token": "fiktiv"}},
        )
        with self.assertRaises(GoogleError), patch("appointments.native.request_json") as http:
            GoogleController(vault).api(self.connection)
        http.assert_not_called()

    def test_offline_disconnect_clears_only_own_local_connection_and_vault(self):
        vault = MemoryVault()
        vault.save(
            vault_key(self.connection),
            {
                "broker": self.config.broker_url,
                "device_id": "fiktiv",
                "device_key": "fiktiv",
                "token": {"access_token": "fiktiv"},
            },
        )

        def offline(url, **kwargs):
            raise GoogleError(0)

        GoogleController(vault, http=offline).disconnect(self.owner, "business")
        self.assertEqual(vault.load(vault_key(self.connection)), {})
        self.assertFalse(CalendarConnection.objects.filter(pk=self.connection.pk).exists())
        self.assertEqual(self.api.writes, [])

    def test_same_calendar_cannot_be_selected_for_both_roles(self):
        CalendarConnection.objects.create(
            owner=self.owner, role="private", calendar_id="business@example.com", state="connected"
        )
        self.connection.calendar_id, self.connection.state = "", "choose"
        self.connection.save()
        vault = MemoryVault()
        vault.save(
            vault_key(self.connection),
            {
                "broker": self.config.broker_url,
                "token": {"access_token": "fiktiver-token", "expires_at": time.time() + 3600},
            },
        )
        result = GoogleController(vault, api_factory=lambda token, role: self.api).choose(
            self.owner, "business", "business@example.com"
        )
        self.connection.refresh_from_db()
        self.assertIn("getrennte", result["message"])
        self.assertEqual(self.connection.calendar_id, "")
        self.assertEqual(self.api.writes, [])

    def test_cancellation_before_first_export_clears_outbox_without_google_write(self):
        self.item.status, self.item.sync_state = "cancelled", "pending"
        self.item.save()
        self.sync()
        self.assertEqual(self.item.sync_state, "local")
        self.assertEqual(self.item.google_event_id, "")
        self.assertEqual(self.api.writes, [])
