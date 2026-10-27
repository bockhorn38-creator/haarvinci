# Haarvinci als Android-APK

Die Android-Version öffnet sich als eigene App auf dem Pixel. Python, Django und die SQLite-Datenbank sind enthalten; ein externer Server oder eine Verbindung zur Windows-App ist für die Kundenverwaltung nicht erforderlich.

## Die aktuelle Testversion 0.4.0

Diese APK ist eine **Entwicklungs-/Testversion für ausschließlich fiktive Kundendaten**. Sie wird mit einem Android-Entwicklungsschlüssel signiert und als APK bereitgestellt, nicht über den Play Store veröffentlicht. Der Fingerabdruck des verwendeten Zertifikats und die SHA-256-Prüfsumme liegen dem Build bei. Für langfristige Updates und einen Produktivbetrieb wird später eine dauerhaft verwaltete Freigabesignierung benötigt. Verschiedene Testbuilds können unterschiedliche Signaturen haben.

Der Zugriff auf die geheimen GitHub-Repository-Einstellungen ist aus dieser Entwicklungsumgebung nicht freigegeben. Es werden deshalb keine bestehenden Signierschlüssel oder GitHub-Secrets überschrieben. Für diese installierbare Test-APK sind zusätzliche Zugangsdaten nicht nötig.

Zielgeräte: Android ab Version 8 (API 26) mit 64-Bit-ARM-Prozessor, insbesondere Google Pixel. Die APK enthält zusätzlich x86-64 für den Emulator. Der tatsächliche Funktionstest wird auf einem emulierten Pixel mit Android 15 durchgeführt; Connys physisches Gerät wird damit nicht als geprüft bezeichnet.

## Installieren und starten

1. Die [geprüfte Android-Test-APK 0.4.0 direkt herunterladen](https://github.com/bockhorn38-creator/haarvinci/raw/refs/heads/android-test-downloads/Haarvinci-Android-Test-0.4.0.apk) (einzelne APK, ca. 52 MB; kein ZIP, keine GitHub-Anmeldung erforderlich).
2. Die heruntergeladene `Haarvinci-Android-Test-0.4.0.apk` auf dem Pixel öffnen. Android führt durch die Installation einer selbst heruntergeladenen App. Falls erforderlich, die Installation aus dieser Quelle für den verwendeten Browser erlauben. Nur die selbst bezogene, geprüfte Datei aus diesem Projekt verwenden.
3. Haarvinci über das App-Symbol öffnen. Beim ersten Start deinen Vornamen, einen Benutzernamen und ein eigenes Passwort mit mindestens zwölf Zeichen festlegen.
4. Zum Ausprobieren können sechs fiktive Testkundinnen angelegt werden. Die bisherigen Funktionen Anlegen, Suchen, Anzeigen, Bearbeiten und Export stehen in der App zur Verfügung.

Die Kundenverwaltung arbeitet lokal und benötigt keine Internetverbindung. Die App speichert ihre Daten im privaten Android-Appordner, nicht im LocalStorage. Eine Anmeldung in Google oder Zugriff auf Kontakte, Fotos oder Standort wird nicht angefordert.

Die Datei liegt als einzelne APK im separaten [GitHub-Download-Zweig](https://github.com/bockhorn38-creator/haarvinci/tree/android-test-downloads) und unterliegt nicht der 30-Tage-Aufbewahrung der ursprünglichen Build-Artefakte. Sie wurde unverändert aus dem bereits erfolgreich geprüften Build übernommen, ohne zusätzlichen Bau oder neue Signierung. Prüfsumme und Zertifikatsinformationen stehen daneben. Die GitHub-Actions-Integration hat das Anlegen des gewünschten Releases mit **HTTP 403: Resource not accessible by integration** verweigert; deshalb wird dieser direkte Datei-Download verwendet. Die Repository-Sichtbarkeit wurde nicht geändert. Die installierte App funktioniert unabhängig von der Verfügbarkeit des Downloads.

Vollständiger Download-Link zum Kopieren:

```text
https://github.com/bockhorn38-creator/haarvinci/raw/refs/heads/android-test-downloads/Haarvinci-Android-Test-0.4.0.apk
```

## Neu in 0.4.0

- Optionales Haarprofil mit Naturhaarfarbe, aktueller Farbe, Struktur, Eigenhaar-/Wunschlänge, Dichte, aktuell getragenen Extensions und individuellen Wünschen.
- Mehrere kundenbezogene Extensions-Positionen mit freien Herstellern, Arten, Farben und Farbcodes, Länge, Gewicht, zusätzlicher Anzahl, exakten Gesamtpreisen, Datum, Lieferstatus und Notizen.
- Anlegen, Bearbeiten und bestätigtes Löschen; Änderungen und gelöschte Positionsstände bleiben in der Kundenhistorie lesbar.
- Eigener Bereich **Extensions** in der unteren Navigation, Suche nach Kundin/Produkt und Filter nach Lieferstatus. Eigene vorhandene Angaben werden beim Erfassen vorgeschlagen.
- Logo, Farben und bisherige Gestaltung bleiben erhalten. Keine Haarlagerverwaltung und keine neuen Sicherungsfunktionen.

### Von 0.3.0 auf diese Testversion wechseln

Der Versionscode wurde von 1 auf 2 erhöht. Der neue CI-Testbuild verwendet einen anderen Entwicklungsschlüssel; eine direkte Aktualisierung der installierten 0.3.0 ist deshalb nicht möglich. Deinstalliere in diesem Fall die alte Haarvinci-Test-App und installiere die neue APK. Dabei werden die bisherigen lokalen Testdaten gelöscht. Der Neuaufbau des Testbestands ist in dieser Entwicklungsphase ausdrücklich vorgesehen. Beim ersten Start können wieder sechs fiktive Kundinnen angelegt werden.

### Die neuen Bereiche ausprobieren

1. Eine fiktive Kundin öffnen und **Bearbeiten → Ihr Haarprofil** aufklappen. Zum Beispiel „Dunkelblond“, „Wellig“, Eigenhaarlänge „25,5“ und Wunschlänge „50“ eintragen. Speichern und nach erneutem Öffnen prüfen.
2. In der Kundenakte **Extensions hinzufügen** wählen. Einen erfundenen Hersteller, eine Art, Farbe, Länge, Gewicht und den Gesamt-Einkaufspreis eintragen. Deutsche Kommawerte wie „149,90“ werden akzeptiert. Speichern.
3. Für dieselbe Kundin eine zweite Position mit anderer Farbe oder Länge anlegen.
4. Eine Position bearbeiten, anschließend die andere löschen und die Löschung bestätigen. Unter **Kundenhistorie** lassen sich Änderungen und der gelöschte Stand aufklappen.
5. Unten **Extensions** öffnen und nach der Kundin, einem Hersteller oder Farbcode suchen. Einen Lieferstatus filtern.
6. Die App schließen und wieder öffnen: Haarprofil und verbliebene Positionen bleiben gespeichert.

Die Extensions-Anzahl ist keine Besuchszahl; Bestelldatum und letzter tatsächlicher Besuch sind unterschiedliche Angaben. Behandlungen, Besuchszahlen und Zahlungen folgen später. Weitere fachliche Details: [EXTENSIONS.md](EXTENSIONS.md).

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
