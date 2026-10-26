# Geprüfter Stand – erste Version

Prüfung am 26. Oktober 2026 in der Cloud-Entwicklungsmaschine.

- Python 3.12, Django 5.2 LTS, PostgreSQL 17.11 und Gunicorn.
- Einrichtung wiederholt ausgeführt: bestehende Konfiguration, Zugang und sechs fiktive Kundinnen bleiben erhalten; keine offenen Migrationen.
- 22 Django-Tests auf einer getrennten echten PostgreSQL-Testdatenbank bestanden. Darunter Kundenabläufe, Suche, Eingabefehler, Benutzertrennung, CSRF, XSS-Ausgabe, Bearbeitungskonflikte, Export, Passwortänderung, Anmeldebegrenzung und Abmelden.
- Echte Chromium-Browserprüfung bestanden: Anmeldung, Suche, Pflichtfeldfehler mit Erhalt der Eingaben, Anlegen, Speichern über Neuladen, Bearbeiten, Export und Abmelden. Zusätzlich Manifest/Symbole und Service Worker erreichbar.
- Formulardarstellung bei 360, 390, 412, 600, 760, 1024 und 1440 Pixeln ohne horizontalen Überlauf geprüft. Desktop und Pixel-Darstellung visuell anhand von Bildschirmfotos kontrolliert.
- PostgreSQL neu gestartet; vollständiger Vergleich der gespeicherten fiktiven Kundendatensätze vor/nach dem Neustart identisch.
- Startsteuerung mit verkürztem Prüfintervall praktisch getestet: Webserver erreichbar, Sicherungsprüfung automatisch ausgeführt und beim Beenden Webserver vollständig gestoppt.
- PostgreSQL-Sicherung erzeugt, Prüfsumme und Archiv geprüft und in eine getrennte Datenbank zurückgespielt. Alle Tabellen und Datensatzanzahlen stimmen mit dem konsistenten Sicherungsmanifest überein. Eine absichtlich beschädigte Kopie wurde wegen abweichender Prüfsumme abgewiesen.
- Ruff, Migrationsprüfung und Djangos Produktions-Sicherheitsprüfung ohne Fehler/Warnungen bestanden.

Nicht geprüft bzw. nicht eingerichtet: physisches Google Pixel, echte HTTPS-Domain, tatsächliche Android-Installation, Internet-Hosting und automatische externe Sicherungen. Der GitHub-Workflow ist vorbereitet; ein Ergebnis auf GitHub ist separat zu prüfen. Spätere Fachmodule sind nicht Teil dieser Version.

Lokale Bildschirmfotos liegen unter `test-results/` und enthalten nur fiktive Daten. Sie gehören ebenso wie `.env`, Zugangspasswort, Datenbank und Sicherungen nicht zum Git-Commit.

## Ergänzung Desktop-Version 0.2

- 28 automatisierte Prüfungen auf PostgreSQL und erneut auf dem tatsächlichen SQLite-Desktop-Profil bestanden, darunter deutsche Namenssuche, Erstzugang, private Zugriffssperre sowie Sicherung/Wiederherstellung.
- Echte Qt-Desktop-Oberfläche einschließlich Ersteinrichtung, Kundin anlegen/bearbeiten, Suche, dauerhaftem Speichern nach Neuladen und Abmelden geprüft.
- Eigenständiges Linux-Programmpaket außerhalb des Quellordners gestartet und denselben Desktop-Ablauf ohne Python-Aufruf geprüft. Das ist eine Paketprüfung; es ersetzt nicht die Windows-Installation.
- Windows-Build, Installer und installierte Desktop-Anwendung werden zusätzlich vom Workflow „Haarvinci für Windows bauen“ geprüft. Der konkrete Windows-Status steht im entsprechenden Workflow-Lauf.
