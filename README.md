# Haarvinci

Connys persönliches Kundenbuch für Haarverlängerung und Haarverdichtung. Die erste Version enthält eine vollständig deutsche, auf Smartphones abgestimmte Oberfläche, Anmeldung und Kundenverwaltung mit echter PostgreSQL-Datenbank.

## Android-Version für das Pixel

Haarvinci wird zusätzlich als eigenständige Android-Test-APK mit lokaler Datenbank gebaut. Installation, Sicherungen, Geräteübernahme und Grenzen der Testsignierung stehen in [docs/ANDROID.md](docs/ANDROID.md). Die APK wird im Workflow „Haarvinci Android-APK prüfen“ auf einem emulierten Pixel installiert und funktional geprüft.

## Windows-Version für PC und Laptop

Die eigenständige Desktop-Version startet per Programmsymbol in einem eigenen Fenster. Sie benötigt für die Nutzung weder Browser noch Python, Docker oder Internet. Installation, Ersteinrichtung, Datensicherung und Bedienung stehen in [docs/DESKTOP.md](docs/DESKTOP.md). Das Windows-Installationspaket wird durch den Workflow „Haarvinci für Windows bauen“ erstellt und geprüft.

Die folgenden bisherigen Startbefehle betreffen die Server-/Entwicklungsversion. Für die Windows-App bitte die Desktop-Anleitung verwenden.

## Was bereits funktioniert

- Geschützte Anmeldung, Abmelden und Passwortänderung; Anmeldebegrenzung bei Fehlversuchen.
- Kundinnen anlegen, nach Name/Telefon/E-Mail suchen, anzeigen und bearbeiten.
- Kontakt, optionale Anschrift und Geburtstag, Beratungsdatum und persönliche Notizen.
- Dauerhafte Speicherung, getrennt von Browser und Webserver; Schutz vor gleichzeitiger Überschreibung.
- Dashboard mit aus den gespeicherten Kundendaten berechneten Kennzahlen.
- Einzelne Kundenakten als JSON-Datei exportieren.
- Lokale PostgreSQL-Sicherungen mit Prüfsummen und Wiederherstellungsprobe.
- Online-PWA mit App-Symbolen. Keine Kundendaten im Offline-Cache.

Google Kalender, Extensions, Behandlungen, Bestellungen, Zahlungen, Statistiken und KI sind bewusst noch nicht implementiert. Ihre fachlichen Grenzen und die vorgesehenen Erweiterungswege stehen in [docs/ARCHITEKTUR.md](docs/ARCHITEKTUR.md).

## Starten – Schritt für Schritt

Die Befehle werden in einem Terminal im Ordner `haarvinci` ausgeführt. Erforderlich sind **Python 3.12**, **uv** und **Docker mit Compose**. Unter Windows eignet sich WSL2 mit Docker Desktop. Die Software läuft auf einem Rechner/Server; das Pixel benötigt nur Chrome.

**1. Einrichten:**

```bash
bash scripts/setup.sh
```

Das Skript installiert die eingefrorenen Abhängigkeiten, erstellt bei Bedarf eine lokale `.env` mit zufälligen Geheimnissen, startet PostgreSQL und richtet die Tabellen ein. Eine vorhandene Konfiguration bleibt erhalten. Das Skript kann erneut ausgeführt werden und überschreibt keine Kundenakten.

**2. Fiktive Testkundinnen und lokalen Testzugang anlegen:**

```bash
uv run python manage.py init_demo
```

Es entstehen sechs ausdrücklich erfundene Kundinnen. Der Benutzername ist `conny`. Das zufällig erzeugte Passwort steht nur in `.local/demo-access.txt`. Öffne diese Datei lokal, beispielsweise im Editor. Sie ist nur für die Dateieigentümerin lesbar und wird nicht in Git gespeichert. Ein erneuter Aufruf setzt das Passwort nicht zurück und dupliziert keine Testdaten.

**3. Anwendung starten:**

```bash
bash scripts/start.sh
```

Öffne auf **demselben Rechner** im Browser die Adresse `http://127.0.0.1:8000`. Lasse das Terminal während der Nutzung geöffnet. Beenden mit `Strg+C`; die Kundendaten bleiben erhalten. Zum erneuten Start genügt derselbe Startbefehl. Der Start erstellt oder prüft zusätzlich die tägliche lokale Sicherung. Solange die App läuft, prüft der Startprozess jede Stunde erneut, ob eine neue Tagessicherung nötig ist. Fehler werden im Terminal protokolliert und nach fünf Minuten erneut versucht. Für Sicherungen bei gestoppter App und externe Kopien siehe unten.

In der Codex-Cloud läuft dieser Server innerhalb der Entwicklungsmaschine. Die interne Adresse ist von deinem privaten Rechner oder Pixel aus nicht erreichbar. Die Einrichtung veröffentlicht keine öffentliche Website. Eine Installation auf deinem Rechner oder ein HTTPS-Hosting ist dafür erforderlich.

Die Cloud kann später vorbereitete Dateien wiederherstellen, aber laufende Prozesse und Docker-Volumes sind nicht garantiert Teil einer solchen Wiederherstellung. Daher liegen PostgreSQL-Sicherungen auch als Dateien unter `.local/backups`. Falls eine neue Maschine eine leere Datenbank hat, **nicht erneut Testdaten anlegen**, sondern die Sicherung gemäß [docs/BETRIEB.md](docs/BETRIEB.md) in eine neue Datenbank zurückspielen.

## Selbst ausprobieren

1. Melde dich mit dem lokalen Testzugang an.
2. Öffne „Kundinnen“ und suche nach „Marie“, einer E-Mail oder Telefonnummer.
3. Wähle „Neue Kundin“, erfasse eine **erfundene** Person und speichere sie. Name und mindestens Telefon oder E-Mail sind erforderlich.
4. Öffne ihre Akte, bearbeite die Notizen und lade die Seite neu. Die Änderung bleibt gespeichert.
5. Exportiere die Akte und prüfe die heruntergeladene JSON-Datei.
6. Öffne „Konto“, ändere bei Bedarf das Passwort und melde dich ab. Ohne Anmeldung darf sich keine Kundenakte öffnen lassen.
7. Stoppe und starte die App erneut. Deine Testkundin bleibt vorhanden.

Bis zur Einrichtung und Prüfung des späteren Produktivbetriebs ausschließlich fiktive Daten verwenden.

## Automatische Tests

PostgreSQL muss laufen. Die Tests verwenden eine separate Testdatenbank und löschen keine Daten aus dem Kundenbuch.

```bash
uv run python manage.py test tests --verbosity 2
uv run ruff check .
uv run python manage.py makemigrations --check --dry-run
```

Für den echten Browser-Test zusätzlich die App in einem anderen Terminal starten:

```bash
uv run python tests/browser_smoke.py
```

Im vorbereiteten Cloud-System wird das bereits installierte Chromium verwendet. Auf anderen Rechnern Chromium über den Paketmanager bereitstellen und `CHROMIUM_PATH` auf dessen Programmdatei setzen, oder die passende Playwright-Version mit `uv run playwright install chromium` installieren. Ohne `CHROMIUM_PATH` nutzt der Test `/usr/bin/chromium`, sofern vorhanden, sonst Playwrights Browser.

Der Browser-Test legt einen eigenen temporären Benutzer mit fiktiven Daten an, prüft den echten Ablauf und entfernt diese Testdaten anschließend. Er prüft Anmeldung, Suche, Formularfehler, Anlegen, Neuladen, Bearbeiten, Export, Abmeldung, App-Dateien und sieben Bildschirmbreiten von 360 bis 1440 Pixeln. Bildschirmfotos landen in `test-results/`. Einen physischen Pixel und die Installation über echtes HTTPS ersetzt diese Prüfung nicht.

## Sicherung und Wiederherstellung

```bash
uv run python scripts/backup.py backup
uv run python scripts/backup.py verify .local/backups/DEINE-SICHERUNG.dump
uv run python scripts/backup.py restore-test .local/backups/DEINE-SICHERUNG.dump
```

Der letzte Befehl spielt die Sicherung tatsächlich in eine getrennte temporäre Datenbank zurück, vergleicht alle Tabellenanzahlen und entfernt nur diese temporäre Datenbank. Die laufende Datenbank bleibt unverändert. Sichere immer die zusammengehörigen `.dump`- und `.json`-Dateien. Vollständige Anleitung, automatischer Zeitplan, externe Kopien und Wiederanlauf: [docs/BETRIEB.md](docs/BETRIEB.md).

## Nutzung auf Connys Google Pixel

Für die reguläre Nutzung braucht Haarvinci eine **HTTPS-Adresse auf einem dauerhaft laufenden Server**, eine PostgreSQL-Datenbank und regelmäßige externe Sicherungen. Die App lässt sich dann in Chrome über „Zum Startbildschirm hinzufügen“ bzw. „App installieren“ installieren. Sie benötigt weiterhin Internet. Es werden keine Kundendaten auf dem Pixel zwischengespeichert.

Ein kleiner verwalteter App-Server plus verwaltetes PostgreSQL ist für den Anfang eine wartungsarme Option. Als grobe Budgetplanung sind je nach Anbieter etwa **15–40 Euro pro Monat** zuzüglich Domain realistisch; dies sind keine geprüften Anbieterpreise. Alternativ ist ein VPS häufig günstiger, erfordert aber eigene Updates, Überwachung und Sicherungen. Es wurde noch kein Hosting bestellt oder eingerichtet. Die konkreten Einstellungen stehen in [docs/BETRIEB.md](docs/BETRIEB.md).

## Entwicklungsstand sichern

Quellcode, Tests, Migration und Dokumentation gehören in Git. `.env`, Testpasswort, Datenbank, Sicherungen und Browser-Artefakte sind bewusst ausgeschlossen. **Ein Git-Commit sichert Programmcode, keine Kundenakten.** Datenbanksicherungen sind unabhängig davon erforderlich.

Abhängigkeiten werden mit `uv sync --frozen` exakt aus `uv.lock` installiert. Aktualisierungen erfolgen bewusst mit neuem Lockfile und erneuten Tests. Der PostgreSQL-Container ist auf den getesteten Image-Digest festgelegt und muss für Sicherheitsupdates ebenfalls bewusst aktualisiert werden.
