# Haarvinci für Windows-PC und Laptop

Haarvinci Desktop öffnet sich als eigenes Programmfenster. Es gibt keine Browser-Adressleiste und du musst keine Internetadresse öffnen. Für die Nutzung der Installationsversion sind weder Python noch Docker, ein separater Server oder eine Internetverbindung notwendig.

## Installieren und zum ersten Mal starten

1. Das Paket **Haarvinci-Windows-Installer** aus dem Windows-Build des Projekts herunterladen. Falls der Download als ZIP kommt, die ZIP-Datei zuerst vollständig entpacken.
2. `Haarvinci-Windows-Setup-0.2.0.exe` per Doppelklick starten und die deutsche Installation abschließen. Die Installation erfolgt im eigenen Windows-Benutzerkonto und benötigt regulär keine Administratorrechte.
3. Haarvinci über das neue Symbol auf dem Desktop oder im Windows-Startmenü öffnen.
4. Beim ersten Start deinen Vornamen, einen Benutzernamen und ein eigenes Passwort mit mindestens zwölf Zeichen festlegen. Das Passwort wird nicht im Klartext gespeichert. Du musst es niemandem mitteilen.
5. „Mit sechs fiktiven Testkundinnen starten“ kann zum Ausprobieren aktiviert bleiben. In dieser ersten Version ausschließlich erfundene Daten verwenden.

Zielplattform: Windows 10 ab Version 1809 und Windows 11 auf 64-Bit-PCs mit Intel-/AMD-Prozessor. Andere Prozessorarchitekturen und ältere Windows-Versionen sind nicht geprüft. Eine digitale Herausgebersignatur für den Installer ist noch nicht eingerichtet; Prüfsummen werden zusammen mit dem Build bereitgestellt.

## Benutzen

Im Bereich „Kundinnen“ findest du deine Kundenakten. Du kannst neue Kundinnen anlegen, nach Namen, Telefonnummern oder E-Mail-Adressen suchen und bestehende Angaben bearbeiten. Namen mit Umlauten und ß werden auch bei Groß-/Kleinschreibung zuverlässig gefunden. Alle Änderungen werden in einer echten lokalen SQLite-Datenbank gespeichert.

Über **Kundenbuch** im oberen Programmmenü gelangst du auch direkt zur Übersicht, zur Suche, zur neuen Kundenakte und zu deinem Konto. Über **Ansicht** lässt sich die Schrift-/Darstellungsgröße verändern. Das Fenster kann vergrößert und maximiert werden.

- `Strg+N`: neue Kundin.
- `Alt+1`: Übersicht; `Alt+2`: Kundinnen; `Alt+3`: Konto.
- `Strg+Umschalt+S`: vollständige Datensicherung.
- **Hilfe → Kurzanleitung** zeigt die wichtigsten Schritte im Programm.

Beim Schließen beendet Haarvinci auch seinen internen Dienst. Die Kundendaten bleiben auf dem Computer und werden beim nächsten Start wieder geladen. Ein normaler Browser kann den internen Zugang nicht ohne den privaten, bei jedem Start erneuerten Programmschlüssel nutzen.

## Daten sichern und wiederherstellen

**Datei → Datensicherung erstellen …** speichert alle Daten in einer einzelnen `.haarvinci`-Datei, beispielsweise auf einen USB-Stick oder getrennten, geschützten Datenträger. Das Programm prüft dabei die Datenbank, ihre Verknüpfungen und eine SHA-256-Prüfsumme.

Zusätzlich aktualisiert Haarvinci automatisch eine lokale Tagessicherung beim Start, bei Änderungen stündlich während des Betriebs und beim Beenden. Frühere Tage bleiben erhalten. Der Ordner ist über **Datei → Datenordner öffnen** erreichbar. Lokale Kopien auf derselben Festplatte schützen nicht vor dem Verlust des Computers; regelmäßig eine getrennte Kopie erstellen.

**Datei → Datensicherung wiederherstellen …** prüft die gewählte Sicherung und zeigt die enthaltene Anzahl der Kundenakten an. Nach deiner Bestätigung wird der aktuelle Datenstand zusätzlich gesichert und die Anwendung mit dem wiederhergestellten Stand neu gestartet. Melde dich mit dem Passwort an, das zum Sicherungszeitpunkt galt. Bei einer leeren Neuinstallation ist die Wiederherstellung bereits vor dem Anlegen eines neuen Zugangs über das Dateimenü möglich.

Die Datenbank und die Sicherungsdateien sind nicht zusätzlich verschlüsselt. Der Schutz des Windows-Benutzerkontos und gegebenenfalls die Laufwerksverschlüsselung schützen die gespeicherten Dateien. Die Anmeldung schützt den Programmzugang; sie ersetzt keine Dateiverschlüsselung. Keine echten Kundendaten verwenden, bevor der reale Einsatz und die Datensicherung geprüft wurden.

Bei einer Deinstallation bleiben die eigenen Daten und Sicherungen erhalten. Eine spätere Neuinstallation kann denselben lokalen Datenbestand wieder öffnen.

## Zwei Rechner

Jeder PC besitzt seinen eigenen Datenbestand. Es gibt noch keine automatische Synchronisierung zwischen PC, Laptop, Pixel oder einer Serverinstallation. Für einen Umzug eine vollständige Sicherung erstellen und auf dem anderen Rechner wiederherstellen. Nicht dieselbe geöffnete Datenbank gleichzeitig über einen freigegebenen Ordner oder Cloud-Synchronisierung bearbeiten.

## Für die Entwicklung

Der Fachkern bleibt Django. Die Desktop-Oberfläche verwendet PySide6/Qt WebEngine in einem abgeschotteten eigenen Fenster. Waitress startet den internen Dienst nur an einer zufälligen lokalen Adresse; ein zusätzlicher privater Header beschränkt den Zugriff auf das Programmfenster. Die Desktop-Datenbank ist SQLite mit echten Transaktionen und geschützter konkurrierender Bearbeitung. Die vorhandene PostgreSQL-Konfiguration ist weiterhin für die Servervariante verfügbar.

Quellstart nach Installation von Python 3.12 und uv:

```bash
uv sync --frozen --extra desktop --group desktop-build
uv run --frozen --extra desktop python -m desktop_app
```

Diese Befehle sind nur für die Entwicklung nötig, nicht für die fertige Windows-Installation.

Windows-Paket selbst bauen (auf Windows mit Inno Setup 6):

```powershell
uv sync --frozen --extra desktop --group desktop-build
uv run --extra desktop python desktop/prepare_assets.py
uv run --extra desktop python desktop/collect_licenses.py
uv run --extra desktop --group desktop-build pyinstaller --noconfirm --clean desktop/Haarvinci.spec
& "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" desktop/installer.iss
```

Der GitHub-Workflow **Haarvinci für Windows bauen** baut dasselbe Paket auf einem echten Windows-Runner, führt die ORM-Tests auf SQLite aus, installiert den erzeugten Installer und testet das tatsächlich installierte Programm mit fiktiven Daten. Nur nach erfolgreicher Prüfung wird der Installer als Build-Artefakt bereitgestellt. Der Build ist keine Veröffentlichung auf einer Website und benötigt keine Produktionszugangsdaten.
