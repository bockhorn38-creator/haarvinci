"""Isolierte Prüfung des Android-Python-Kerns vor dem eigentlichen APK-Test."""

import http.client
import http.cookiejar
import json
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "android/app/src/main/python"))
from android_backend import runtime  # noqa: E402


def main():
    with tempfile.TemporaryDirectory(prefix="haarvinci-android-") as temporary:
        info = json.loads(runtime.start(temporary, str(ROOT)))
        origin = info["origin"]
        cookies = http.cookiejar.CookieJar()
        client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))

        def gate():
            cookies.clear()
            cookies.set_cookie(
                http.cookiejar.Cookie(
                    0,
                    "haarvinci_android_gate",
                    info["token"],
                    None,
                    False,
                    "127.0.0.1",
                    False,
                    False,
                    "/",
                    True,
                    False,
                    None,
                    True,
                    None,
                    None,
                    {},
                )
            )

        def get(path):
            response = client.open(origin + path, timeout=20)
            return response.read().decode(), response.url

        def post(path, data):
            html, _ = get(path)
            csrf = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html).group(1)
            response = client.open(
                origin + path,
                urllib.parse.urlencode(data | {"csrfmiddlewaretoken": csrf}).encode(),
                timeout=20,
            )
            return response.read().decode(), response.url

        try:
            try:
                urllib.request.urlopen(origin + "/bereit/")
                raise AssertionError("Android-Zugriff ohne App-Cookie erlaubt")
            except urllib.error.HTTPError as error:
                assert error.code == 403
            gate()
            page, url = get("/")
            assert url.endswith("/einrichten/")
            assert "DEINE ANDROID-APP" in page
            password = "Fiktives-Android-Testpasswort-2026!"
            page, url = post(
                "/einrichten/",
                {
                    "username": "conny-android-test",
                    "first_name": "Conny",
                    "password1": password,
                    "password2": password,
                    "demo_data": "on",
                },
            )
            assert "Schön, dass du da bist, Conny" in page
            data = {
                "first_name": "Mila",
                "last_name": "Testgarten",
                "phone": "+49 151 0000 0199",
                "email": "mila@example.com",
                "first_consultation": "2026-10-01",
                "notes": "Vor der Sicherung",
                "version": "1",
                "natural_color": "Dunkelblond",
                "natural_length": "25,5",
            }
            page, url = post("/kundinnen/neu/", data)
            detail = urllib.parse.urlsplit(url).path
            assert "Vor der Sicherung" in page
            position_data = {
                "manufacturer": "Fiktivhaar Atelier",
                "extension_type": "Tape-Ins",
                "color": "Kupfer",
                "color_code": "#18/22",
                "length_cm": "50",
                "weight_g": "100,25",
                "purchase_price": "149,90",
                "sale_price": "249,95",
                "assigned_on": "2026-10-01",
                "version": "1",
            }
            page, _ = post(detail + "extensions/neu/", position_data)
            assert "Fiktivhaar Atelier" in page and "149,90" in page
            position_id = re.search(r'data-position="([^"]+)"', page).group(1)
            position_edit = detail + "extensions/" + position_id + "/bearbeiten/"
            archive = Path(temporary) / "test.haarvinci"
            runtime.export_backup(str(archive))
            assert json.loads(runtime.inspect_backup(str(archive)))["customers"] == 7
            post(detail + "bearbeiten/", data | {"notes": "Nach der Sicherung"})
            post(position_edit, position_data | {"color": "Schwarz nach Sicherung"})
            info = json.loads(runtime.restore(str(archive)))
            origin = info["origin"]
            gate()
            post("/anmelden/", {"username": "conny-android-test", "password": password})
            page, _ = get(detail)
            assert "Vor der Sicherung" in page and "Nach der Sicherung" not in page
            assert "25,5 cm" in page and "Kupfer" in page and "Schwarz nach Sicherung" not in page
            assert "149,90" in page
            page, _ = get("/konto/")
            assert "haarvinci://backup" in page and "Deine Daten auf dem Pixel" in page
            parts = urllib.parse.urlsplit(origin)
            keepalive = http.client.HTTPConnection(parts.hostname, parts.port)
            keepalive.request(
                "GET", "/bereit/", headers={"Cookie": "haarvinci_android_gate=" + info["token"]}
            )
            response = keepalive.getresponse()
            assert response.status == 200
            response.read()
            old_thread = runtime._runtime.thread
            runtime._runtime.stop()
            assert not old_thread.is_alive(), "Interner Dienst blieb bei Keep-Alive geöffnet"
            keepalive.close()
            print(
                "Android-Kern geprüft: Cookie-Zugriffsschutz, Ersteinrichtung, Kundin mit Haarprofil und Extensions speichern, Sicherung und echte Wiederherstellung mit erneuter Anmeldung."
            )
        finally:
            runtime._runtime.stop()


if __name__ == "__main__":
    main()
