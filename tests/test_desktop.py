import hashlib
import json
import sqlite3
import tempfile
import zipfile
from contextlib import closing
from pathlib import Path
from unittest import TestCase

from django.contrib.auth import get_user_model
from django.test import Client, override_settings
from django.test import TestCase as DjangoTestCase

from desktop_app.storage import (
    BackupError,
    create_backup,
    installation_secret,
    restore_backup,
    validate_backup,
)


class DesktopStorageTests(TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.database = self.root / "haarvinci.sqlite3"
        with closing(sqlite3.connect(self.database)) as db, db:
            db.executescript(
                "CREATE TABLE auth_user(id INTEGER PRIMARY KEY); CREATE TABLE django_migrations(id INTEGER PRIMARY KEY); CREATE TABLE customers_customer(id INTEGER PRIMARY KEY, name TEXT); INSERT INTO customers_customer(name) VALUES ('Fiktive Kundin');"
            )

    def test_installation_secret_is_random_and_stable(self):
        first = installation_secret(self.root)
        self.assertGreaterEqual(len(first), 50)
        self.assertEqual(first, installation_secret(self.root))
        with tempfile.TemporaryDirectory() as other:
            self.assertNotEqual(first, installation_secret(Path(other)))

    def test_backup_restores_saved_content_and_preserves_previous_state(self):
        archive = create_backup(self.database, self.root / "sicherung.haarvinci")
        metadata, _ = validate_backup(archive)
        self.assertEqual(metadata["tables"]["customers_customer"], 1)
        with closing(sqlite3.connect(self.database)) as db, db:
            db.execute("UPDATE customers_customer SET name='Vor Wiederherstellung'")
        restore_backup(archive, self.root)
        with closing(sqlite3.connect(self.database)) as db, db:
            self.assertEqual(
                db.execute("SELECT name FROM customers_customer").fetchone()[0], "Fiktive Kundin"
            )
        safety = list((self.root / "Sicherungen").glob("*.haarvinci"))
        self.assertEqual(len(safety), 1)
        _, content = validate_backup(safety[0])
        check = self.root / "safety.sqlite3"
        check.write_bytes(content)
        with closing(sqlite3.connect(check)) as db, db:
            self.assertEqual(
                db.execute("SELECT name FROM customers_customer").fetchone()[0],
                "Vor Wiederherstellung",
            )

    def test_corrupted_backup_is_rejected_without_changing_database(self):
        archive = create_backup(self.database, self.root / "sicherung.haarvinci")
        with zipfile.ZipFile(archive) as bundle:
            metadata = json.loads(bundle.read("manifest.json"))
            content = bundle.read("datenbank.sqlite3")
        metadata["sha256"] = "0" * 64
        broken = self.root / "broken.haarvinci"
        with zipfile.ZipFile(broken, "w") as bundle:
            bundle.writestr("manifest.json", json.dumps(metadata))
            bundle.writestr("datenbank.sqlite3", content)
        before = hashlib.sha256(self.database.read_bytes()).hexdigest()
        with self.assertRaises(BackupError):
            restore_backup(broken, self.root)
        self.assertEqual(before, hashlib.sha256(self.database.read_bytes()).hexdigest())


@override_settings(
    ROOT_URLCONF="desktop_app.urls",
    DESKTOP_MODE=True,
    DESKTOP_TOKEN="a-private-test-instance-token",
    SECURE_SSL_REDIRECT=False,
    AXES_ENABLED=False,
)
class DesktopSetupTests(DjangoTestCase):
    def test_first_run_sets_password_and_creates_only_fictional_data(self):
        response = self.client.post(
            "/einrichten/",
            {
                "username": "conny-local",
                "first_name": "Conny",
                "password1": "Ein-Neues-Testpasswort-2026!",
                "password2": "Ein-Neues-Testpasswort-2026!",
                "demo_data": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        user = get_user_model().objects.get()
        self.assertTrue(user.check_password("Ein-Neues-Testpasswort-2026!"))
        self.assertFalse(user.is_superuser)
        self.assertEqual(user.customers.count(), 6)
        self.assertEqual(self.client.get("/einrichten/").status_code, 404)

    @override_settings(MIDDLEWARE=["desktop_app.middleware.DesktopGateMiddleware"])
    def test_desktop_server_rejects_browser_requests_without_private_header(self):
        client = Client()
        self.assertEqual(client.get("/bereit/").status_code, 403)
        self.assertEqual(client.get("/bereit/", HTTP_X_HAARVINCI_DESKTOP="wrong").status_code, 403)
        self.assertEqual(
            client.get(
                "/bereit/", HTTP_X_HAARVINCI_DESKTOP="a-private-test-instance-token"
            ).status_code,
            200,
        )
