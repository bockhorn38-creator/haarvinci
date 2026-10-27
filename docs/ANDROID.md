# Haarvinci als Android-APK

Die Android-Version öffnet sich als eigene App auf dem Pixel. Python, Django und die SQLite-Datenbank sind enthalten; ein externer Server oder eine Verbindung zur Windows-App ist für die Kundenverwaltung nicht erforderlich.

## Die erste Testversion

Diese erste APK ist eine **Entwicklungs-/Testversion für ausschließlich fiktive Kundendaten**. Sie wird mit einem Android-Entwicklungsschlüssel signiert und als APK bereitgestellt, nicht über den Play Store veröffentlicht. Der Fingerabdruck des verwendeten Zertifikats und die SHA-256-Prüfsumme liegen dem Build bei. Für langfristige Updates und einen Produktivbetrieb wird später eine dauerhaft verwaltete Freigabesignierung benötigt. Verschiedene Testbuilds können unterschiedliche Signaturen haben.

Der Zugriff auf die geheimen GitHub-Repository-Einstellungen ist aus dieser Entwicklungsumgebung nicht freigegeben. Es werden deshalb keine bestehenden Signierschlüssel oder GitHub-Secrets überschrieben. Für diese installierbare Test-APK sind zusätzliche Zugangsdaten nicht nötig.

Zielgeräte: Android ab Version 8 (API 26) mit 64-Bit-ARM-Prozessor, insbesondere Google Pixel. Die APK enthält zusätzlich x86-64 für den Emulator. Der tatsächliche Funktionstest wird auf einem emulierten Pixel mit Android 15 durchgeführt; Connys physisches Gerät wird damit nicht als geprüft bezeichnet.

## Installieren und starten

1. Das geprüfte Paket **Haarvinci-Android-Test-APK** aus dem Android-Workflow herunterladen und die ZIP-Datei entpacken.
2. Die darin enthaltene `Haarvinci-Android-Test-0.3.0.apk` auf dem Pixel öffnen. Android führt durch die Installation einer selbst heruntergeladenen App. Nur die selbst bezogene, geprüfte Datei aus diesem Projekt verwenden.
3. Haarvinci über das App-Symbol öffnen. Beim ersten Start deinen Vornamen, einen Benutzernamen und ein eigenes Passwort mit mindestens zwölf Zeichen festlegen.
4. Zum Ausprobieren können sechs fiktive Testkundinnen angelegt werden. Die bisherigen Funktionen Anlegen, Suchen, Anzeigen, Bearbeiten und Export stehen in der App zur Verfügung.

Die Kundenverwaltung arbeitet lokal und benötigt keine Internetverbindung. Die App speichert ihre Daten im privaten Android-Appordner, nicht im LocalStorage. Eine Anmeldung in Google oder Zugriff auf Kontakte, Fotos oder Standort wird nicht angefordert.

## Sicherungen und Übernahme zwischen Rechner und Pixel

Im Drei-Punkte-Menü oder unter **Konto → Datensicherung erstellen** lässt sich eine vollständige `.haarvinci`-Datei über die Android-Dateiauswahl speichern. Wähle regelmäßig einen getrennten, geschützten Speicherort. Die App erhält nur Zugriff auf die ausgewählte Datei.

**Sicherung wiederherstellen** prüft die Datei und zeigt die Anzahl der enthaltenen Kundenakten. Nach der Bestätigung wird zuerst der aktuelle Stand zusätzlich gesichert und dann der gewählte Stand geladen. Anschließend mit dem Passwort des Sicherungszeitpunkts anmelden. Bei einer leeren Installation ist die Wiederherstellung auch über das Drei-Punkte-Menü vor der Ersteinrichtung verfügbar.

Das Format ist mit der Windows-Desktop-Version kompatibel. Eine Windows-Sicherung kann so manuell auf das Pixel übertragen und dort wiederhergestellt werden. Das ersetzt keine automatische Synchronisierung: Jedes Gerät besitzt seinen eigenen Datenbestand.

Die App aktualisiert zusätzlich lokale Tagessicherungen beim Öffnen, stündlich während des laufenden Betriebs sowie beim Wechsel in den Hintergrund. Eine lokale Kopie schützt nicht vor Geräteverlust. Sichere regelmäßig eine Datei außerhalb der App. Eine Deinstallation von Android-Apps löscht deren private Daten – **vor einer Deinstallation oder einem möglicherweise inkompatiblen Test-Update immer extern sichern**.

Die Sicherungen sind nicht zusätzlich verschlüsselt. Nutze ein geschütztes Geräteprofil und sichere die Dateien an einem geschützten Ort. Automatische Android-Cloud-Sicherungen der App sind deaktiviert; eine Datei wird nur nach eigener Auswahl exportiert.

## Architektur und Bau

- Native Android-Hülle in Java mit System-WebView; keine freie Browsernavigation und keine JavaScript-Brücke zu Dateisystemfunktionen.
- Chaquopy 17.2 mit Python 3.12 für denselben Django-Fachkern wie in der Desktop-App.
- Waitress nur auf 127.0.0.1 mit zufälligem Port. Ein privates HttpOnly-Cookie bindet den Zugriff an die App-Sitzung. Anmeldung und CSRF-Schutz bleiben zusätzlich aktiv.
- SQLite mit Transaktionen, Unicode-Suche und denselben Kundenmodellen/Migrationen.
- Native Android-Dateiauswahl für Export und Wiederherstellung. Keine umfassende Speicherberechtigung.
- Gradle-Wrapper und Distribution sind per veröffentlichter SHA-256-Prüfsumme geprüft. Android-Python-Abhängigkeiten werden aus uv.lock abgeleitet und mit Paket-Hashes installiert.

Bau auf einem Entwicklungssystem mit JDK 21, Python 3.12 und Android SDK 36:

```bash
python android/prepare_sources.py
android/gradlew -p android --no-daemon :app:testDebugUnitTest :app:assembleDebug :app:assembleDebugAndroidTest
```

Die Paketversionen werden bewusst mit `python android/refresh_requirements.py` aus `uv.lock` übernommen. Den erzeugten Lockfile gemeinsam mit Änderungen prüfen und speichern.

Der GitHub-Workflow **Haarvinci Android-APK prüfen** baut das APK, installiert es auf einem Android-Emulator und prüft den echten Ablauf inklusive Dateiauswahl, Sicherung/Rückspielung, Abmelden und Neustart des App-Prozesses. Das APK wird erst nach erfolgreicher Prüfung als Installationsartefakt bereitgestellt. Weder API-Schlüssel noch echte Kundendaten werden dafür benötigt.
