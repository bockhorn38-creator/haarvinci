import json
from datetime import timedelta
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from cryptography.fernet import Fernet
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from google_broker import provider
from google_broker.models import Device, Handoff
from google_broker.views import challenge, digest


@override_settings(
    ROOT_URLCONF="google_broker.urls",
    SECURE_SSL_REDIRECT=False,
    GOOGLE_CLIENT_ID="fiktiver-testclient.apps.googleusercontent.com",
    GOOGLE_CLIENT_SECRET="nur-fiktives-test-client-geheimnis",
    GOOGLE_REDIRECT_URI="https://auth.example.com/oauth/google/callback/",
    GOOGLE_HANDOFF_KEY=Fernet.generate_key().decode(),
)
class BrokerTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.verifier = "v" * 64
        self.device_key = "d" * 64

    def post(self, url, data):
        return self.client.post(url, json.dumps(data), content_type="application/json")

    def start(self, role="business"):
        response = self.post(
            "/mobil/start/",
            {"role": role, "challenge": challenge(self.verifier), "device_key": self.device_key},
        )
        self.assertEqual(response.status_code, 200)
        result = response.json()
        params = parse_qs(urlsplit(result["authorization_url"]).query)
        self.assertEqual(urlsplit(result["authorization_url"]).hostname, "accounts.google.com")
        self.assertEqual(
            params["redirect_uri"][0], "https://auth.example.com/oauth/google/callback/"
        )
        self.assertEqual(params["code_challenge_method"], ["S256"])
        self.assertNotIn("client_secret", params)
        return result, params["state"][0]

    def authorize(self, state):
        token = {
            "access_token": "fiktiver-zugangstoken",
            "refresh_token": "fiktiver-erneuerungstoken",
            "expires_in": 3600,
        }
        with patch.object(provider, "exchange", return_value=token):
            response = self.client.get(
                "/oauth/google/callback/", {"state": state, "code": "fiktiver-code"}
            )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "fiktiver-zugangstoken")

    def test_oauth_code_handoff_is_pkce_protected_encrypted_and_single_use(self):
        result, state = self.start()
        self.authorize(state)
        row = Handoff.objects.get()
        self.assertNotIn("fiktiver-zugangstoken", row.encrypted_payload)
        self.assertEqual(
            self.post(
                "/mobil/abschliessen/", {"id": result["id"], "verifier": "wrong"}
            ).status_code,
            400,
        )
        response = self.post(
            "/mobil/abschliessen/", {"id": result["id"], "verifier": self.verifier}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["token"]["access_token"], "fiktiver-zugangstoken")
        self.assertEqual(Handoff.objects.count(), 0)
        self.assertEqual(
            self.post(
                "/mobil/abschliessen/", {"id": result["id"], "verifier": self.verifier}
            ).status_code,
            400,
        )
        self.assertNotIn(
            "fiktiver-erneuerungstoken", json.dumps(list(Device.objects.values()), default=str)
        )

    def test_private_flow_requests_only_calendar_list_and_availability(self):
        result, _ = self.start("private")
        scopes = parse_qs(urlsplit(result["authorization_url"]).query)["scope"][0].split()
        self.assertIn("https://www.googleapis.com/auth/calendar.events.freebusy", scopes)
        self.assertNotIn("https://www.googleapis.com/auth/calendar.events.owned", scopes)

    def test_wrong_oauth_state_cannot_exchange_or_change_pending_handoff(self):
        self.start()
        with patch.object(provider, "exchange") as exchange:
            self.assertEqual(
                self.client.get(
                    "/oauth/google/callback/", {"state": "unbekannt", "code": "code"}
                ).status_code,
                400,
            )
            exchange.assert_not_called()
        self.assertEqual(Handoff.objects.get().status, "pending")

    def test_cancelled_expired_and_invalid_handoffs_do_not_return_tokens(self):
        result, state = self.start()
        self.client.get("/oauth/google/callback/", {"state": state, "error": "access_denied"})
        self.assertEqual(
            self.post(
                "/mobil/abschliessen/", {"id": result["id"], "verifier": self.verifier}
            ).status_code,
            400,
        )
        result, state = self.start()
        Handoff.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(
            self.client.get(
                "/oauth/google/callback/", {"state": state, "code": "code"}
            ).status_code,
            400,
        )
        self.assertEqual(
            self.post(
                "/mobil/abschliessen/", {"id": "kein-uuid", "verifier": self.verifier}
            ).status_code,
            400,
        )

    def test_pending_response_contains_no_credentials(self):
        result, _ = self.start()
        response = self.post(
            "/mobil/abschliessen/", {"id": result["id"], "verifier": self.verifier}
        )
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json(), {"status": "pending"})

    def test_refresh_requires_bound_device_secret_and_never_stores_tokens(self):
        device = Device.objects.create(secret_hash=digest(self.device_key), role="private")
        data = {
            "device_id": str(device.pk),
            "device_key": "wrong",
            "refresh_token": "fiktiver-refresh",
        }
        with patch.object(
            provider, "refresh", return_value={"access_token": "fiktiver-neuer-token"}
        ) as refresh:
            self.assertEqual(self.post("/mobil/erneuern/", data).status_code, 403)
            refresh.assert_not_called()
            data["device_key"] = self.device_key
            response = self.post("/mobil/erneuern/", data)
            self.assertEqual(response.status_code, 200)
            refresh.assert_called_once_with("private", "fiktiver-refresh")
        self.assertNotIn(
            "fiktiver-neuer-token", json.dumps(list(Device.objects.values()), default=str)
        )

    def test_disconnect_requires_device_proof_and_only_removes_device_registration(self):
        device = Device.objects.create(secret_hash=digest(self.device_key), role="business")
        self.assertEqual(
            self.post(
                "/mobil/trennen/", {"device_id": str(device.pk), "device_key": "wrong"}
            ).status_code,
            403,
        )
        self.assertEqual(
            self.post(
                "/mobil/trennen/", {"device_id": str(device.pk), "device_key": self.device_key}
            ).status_code,
            200,
        )
        self.assertEqual(Device.objects.count(), 0)
