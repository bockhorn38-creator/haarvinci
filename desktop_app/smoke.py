"""Prüft die wirkliche Desktop-Oberfläche; alle Daten liegen im isolierten Testordner."""

import json
import secrets
import sqlite3
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

from PySide6.QtCore import QTimer, QUrl

from .storage import create_backup, restore_backup, validate_backup


class DesktopSmoke:
    def __init__(self, window, token, result_path, app):
        self.window = window
        self.token = token
        self.result_path = result_path.resolve()
        self.result_path.parent.mkdir(parents=True, exist_ok=True)
        self.app = app
        self.stage = 0
        self.attempts = 0
        self.password = secrets.token_urlsafe(25)
        self.detail_url = ""
        self.timer = QTimer(window)
        self.timer.setInterval(300)
        self.timer.timeout.connect(self.inspect)
        self.busy = False

    def start(self):
        try:
            try:
                urllib.request.urlopen(self.window.origin + "/bereit/", timeout=5)
                raise AssertionError(
                    "Zugang ohne privaten Programmschlüssel wurde nicht abgewiesen"
                )
            except urllib.error.HTTPError as error:
                assert error.code == 403
            request = urllib.request.Request(
                self.window.origin + "/bereit/", headers={"X-Haarvinci-Desktop": self.token}
            )
            assert json.load(urllib.request.urlopen(request, timeout=5)) == {"status": "ok"}
            self.timer.start()
        except Exception as error:
            self.fail(error)

    def inspect(self):
        if self.busy:
            return
        self.attempts += 1
        if self.attempts > 200:
            self.fail(
                AssertionError(f"Desktop-Prüfung bei Schritt {self.stage} nicht abgeschlossen")
            )
            return
        self.busy = True
        self.window.page.runJavaScript(
            "JSON.stringify({text: document.body ? document.body.innerText : '', path: location.pathname, lang:document.documentElement.lang, background: document.body ? getComputedStyle(document.body).backgroundColor : ''})",
            self.receive,
        )

    def fill(self, fields):
        script = f"for (const [key,value] of Object.entries({json.dumps(fields)})) {{ const input=document.querySelector('[name=\"'+key+'\"]'); input.value=value; }} document.querySelector('form').requestSubmit();"
        self.window.page.runJavaScript(script)

    def capture(self, filename, next_stage, path):
        self.window.grab().save(str(self.result_path.parent / filename))
        self.stage = next_stage
        self.navigate(path)

    def navigate(self, path):
        self.window.view.setUrl(QUrl(self.window.origin + path))

    def receive(self, value):
        self.busy = False
        try:
            data = json.loads(value)
            text, path = data["text"], data["path"]
            assert data["lang"] == "de"
            if self.stage == 0 and path == "/einrichten/" and "Mach es zu deinem." in text:
                assert data["background"] == "rgb(250, 247, 243)"
                self.stage = 1
                self.fill(
                    {
                        "first_name": "Conny",
                        "username": "desktop-test",
                        "password1": self.password,
                        "password2": self.password,
                    }
                )
            elif self.stage == 1 and path == "/" and "Schön, dass du da bist, Conny." in text:
                self.stage = -1
                QTimer.singleShot(
                    900, lambda: self.capture("desktop-uebersicht.png", 2, "/kundinnen/neu/")
                )
            elif self.stage == 2 and path == "/kundinnen/neu/" and "Kundin speichern" in text:
                self.stage = 3
                self.fill(
                    {
                        "first_name": "Mila",
                        "last_name": "Testgarten",
                        "phone": "+49 151 0000 0199",
                        "email": "mila@example.com",
                        "first_consultation": "2026-10-01",
                        "notes": "Fiktive Desktop-Testkundin.",
                    }
                )
            elif self.stage == 3 and "Mila Testgarten" in text and "Persönliche Notizen" in text:
                self.detail_url = path
                self.stage = 4
                self.navigate(path + "bearbeiten/")
            elif (
                self.stage == 4 and path.endswith("/bearbeiten/") and "Änderungen speichern" in text
            ):
                self.stage = 5
                self.fill({"notes": "Geändert und dauerhaft in der Desktop-Datenbank gespeichert."})
            elif (
                self.stage == 5
                and path == self.detail_url
                and "dauerhaft in der Desktop-Datenbank" in text
            ):
                self.stage = 6
                self.window.view.reload()
            elif (
                self.stage == 6
                and path == self.detail_url
                and "dauerhaft in der Desktop-Datenbank" in text
            ):
                self.stage = 7
                self.navigate("/kundinnen/?q=Mila+Testgarten")
            elif self.stage == 7 and path == "/kundinnen/" and "1 Ergebnis" in text:
                assert "Mila Testgarten" in text
                assert "Marie Sommer" not in text
                self.window.grab().save(str(self.result_path.parent / "desktop-kundinnen.png"))
                archive = self.result_path.parent / "desktop-test.haarvinci"
                create_backup(self.window.data_dir / "haarvinci.sqlite3", archive)
                metadata, _ = validate_backup(archive)
                assert metadata["tables"]["customers_customer"] == 7
                with tempfile.TemporaryDirectory() as temporary:
                    target = Path(temporary)
                    restore_backup(archive, target)
                    with sqlite3.connect(target / "haarvinci.sqlite3") as db:
                        assert (
                            db.execute("SELECT count(*) FROM customers_customer").fetchone()[0] == 7
                        )
                        db.execute("DELETE FROM customers_customer")
                    restore_backup(archive, target)
                    with sqlite3.connect(target / "haarvinci.sqlite3") as db:
                        assert (
                            db.execute("SELECT count(*) FROM customers_customer").fetchone()[0] == 7
                        )
                    assert list((target / "Sicherungen").glob("Vor-Wiederherstellung-*.haarvinci"))
                self.stage = 8
                self.navigate("/konto/")
            elif self.stage == 8 and path == "/konto/" and "Sicher abmelden" in text:
                self.stage = 9
                self.window.page.runJavaScript(
                    "document.querySelector('form[action=\"/abmelden/\"]').requestSubmit()"
                )
            elif self.stage == 9 and path == "/anmelden/":
                self.stage = 10
                self.navigate(self.detail_url)
            elif self.stage == 10 and path == "/anmelden/" and "Kundenbuch öffnen" in text:
                self.timer.stop()
                self.result_path.write_text(
                    json.dumps(
                        {
                            "status": "passed",
                            "checks": [
                                "native-window",
                                "german-interface",
                                "private-local-access",
                                "first-run-password",
                                "customer-create",
                                "customer-edit",
                                "persistence-after-reload",
                                "search",
                                "backup-validation",
                                "full-restore",
                                "safety-backup-before-restore",
                                "logout",
                            ],
                        },
                        indent=2,
                    ),
                    encoding="utf-8",
                )
                self.app.exit(0)
        except Exception as error:
            self.fail(error)

    def fail(self, error):
        self.timer.stop()
        self.result_path.write_text(
            json.dumps({"status": "failed", "stage": self.stage, "error": str(error)}),
            encoding="utf-8",
        )
        self.app.exit(1)
