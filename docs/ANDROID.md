# Haarvinci als Android-APK

Die Android-Version öffnet sich als eigene App auf dem Pixel. Python, Django und die SQLite-Datenbank sind enthalten; ein externer Server oder eine Verbindung zur Windows-App ist für die Kundenverwaltung nicht erforderlich.

## Die aktuelle Testversion 0.5.1

Diese APK ist eine **Entwicklungs-/Testversion für ausschließlich fiktive Kundendaten**. Sie wird mit einem Android-Entwicklungsschlüssel signiert und als APK bereitgestellt, nicht über den Play Store veröffentlicht. Der Fingerabdruck des verwendeten Zertifikats und die SHA-256-Prüfsumme liegen dem Build bei. Für langfristige Updates und einen Produktivbetrieb wird später eine dauerhaft verwaltete Freigabesignierung benötigt. Verschiedene Testbuilds können unterschiedliche Signaturen haben.

Der Zugriff auf die geheimen GitHub-Repository-Einstellungen ist aus dieser Entwicklungsumgebung nicht freigegeben. Es werden deshalb keine bestehenden Signierschlüssel oder GitHub-Secrets überschrieben. Für diese installierbare Test-APK sind zusätzliche Zugangsdaten nicht nötig.

Zielgeräte: Android ab Version 8 (API 26) mit 64-Bit-ARM-Prozessor, insbesondere Google Pixel. Die APK enthält zusätzlich x86-64 für den Emulator. Der tatsächliche Funktionstest wird auf einem emulierten Pixel mit Android 15 durchgeführt; Connys physisches Gerät wird damit nicht als geprüft bezeichnet.

## Installieren und starten

1. Die [geprüfte Android-Test-APK 0.5.1 direkt herunterladen](https://github.com/bockhorn38-creator/haarvinci/raw/refs/heads/android-test-downloads/Haarvinci-Android-Test-0.5.1.apk) (einzelne APK, ca. 55 MB; kein ZIP, keine GitHub-Anmeldung erforderlich).
2. Die heruntergeladene `Haarvinci-Android-Test-0.5.1.apk` auf dem Pixel öffnen. Android führt durch die Installation einer selbst heruntergeladenen App. Falls erforderlich, die Installation aus dieser Quelle für den verwendeten Browser erlauben. Nur die selbst bezogene, geprüfte Datei aus diesem Projekt verwenden.
3. Haarvinci über das App-Symbol öffnen. Beim ersten Start deinen Vornamen, einen Benutzernamen und ein eigenes Passwort mit mindestens zwölf Zeichen festlegen.
4. Zum Ausprobieren können sechs fiktive Testkundinnen angelegt werden. Die bisherigen Funktionen Anlegen, Suchen, Anzeigen, Bearbeiten und Export stehen in der App zur Verfügung.

Die Kundenverwaltung arbeitet lokal und benötigt keine Internetverbindung. Die App speichert ihre Daten im privaten Android-Appordner, nicht im LocalStorage. Kontakte, Fotos und Standort werden nicht angefordert. Für die optionale Kalenderverbindung werden die Android-Kalenderberechtigungen nach deiner ausdrücklichen Auswahl benötigt; die Google-Konten sind bereits im System eingerichtet.

Die Datei liegt als einzelne APK im separaten [GitHub-Download-Zweig](https://github.com/bockhorn38-creator/haarvinci/tree/android-test-downloads) und unterliegt nicht der 30-Tage-Aufbewahrung der ursprünglichen Build-Artefakte. Sie wurde unverändert aus dem bereits erfolgreich geprüften Build übernommen, ohne zusätzlichen Bau oder neue Signierung. Prüfsumme und Zertifikatsinformationen stehen im Unterordner `0.5.1` daneben. Die GitHub-Actions-Integration hat das Anlegen eines Releases zuvor mit **HTTP 403: Resource not accessible by integration** verweigert; deshalb wird dieser direkte Datei-Download verwendet. Die Repository-Sichtbarkeit wurde nicht geändert. Die installierte App funktioniert unabhängig von der Verfügbarkeit des Downloads.

Vollständiger Download-Link zum Kopieren:

```text
https://github.com/bockhorn38-creator/haarvinci/raw/refs/heads/android-test-downloads/Haarvinci-Android-Test-0.5.1.apk
```

## Neu in 0.5.1: direkt vom Pixel übernehmen

- **Aus ChatGPT einfügen:** Antworttext kopieren und im Drei-Punkte-Menü einfügen oder über Android an Haarvinci teilen. Die Vorschau erkennt Kundendaten, Haarprofile, Extensions und Termine gemeinsam. Fehlende Angaben ergänzen und vorhandene Kundinnen manuell auswählen. Erst **Jetzt verbindlich übernehmen** speichert. [Formatvorlage und Prompt](CHATGPT-IMPORT.md).
- **Gerätekalender:** Im Kalender den entsprechenden Link öffnen und geschäftlichen sowie privaten Android-Kalender auswählen. Kein eigener Server, keine Domain oder Google-Cloud-Konfiguration erforderlich. Privat erscheinen nur Belegt-Zeiten. Änderungen an fremden Terminen sind gesperrt; unklare Zuordnungen oder beidseitige Änderungen verlangen eine Prüfung. [Einrichtung und Grenzen](ANDROID-GERAETEKALENDER.md).
- Ohne OpenAI-API. Teilt ChatGPT nur einen Link, den vollständigen Antworttext kopieren und die Zwischenablage verwenden. Die konkrete ChatGPT-App und der Google-Kontosync bleiben Pixel-Prüfungen.

## Neu in 0.5.0: Kalender und Termine

1. Unten **Kalender** öffnen. **Tag**, **Woche**, **Monat**, Pfeile und **Heute** ausprobieren.
2. **Neuer Termin** wählen, eine fiktive Kundin und Terminart auswählen, Datum und Uhrzeiten eintragen. Die Dauer wird automatisch berechnet.
3. Einen Puffer nach dem Termin eintragen. Einen zweiten Termin in diese Zeit legen: Die App muss warnen und verlangt eine bewusste Bestätigung, falls du den Konflikt trotzdem übernehmen möchtest.
4. Den Termin öffnen und **Bearbeiten / verschieben** oder **Termin absagen** ausprobieren. Absagen bleiben sichtbar und zählen nicht als Besuche.
5. Einen vergangenen fiktiven Termin als **Abgeschlossen** speichern. Die Kundenakte zeigt den Besuch sowie den nächsten und letzten abgeschlossenen Termin. Zukünftige Termine lassen sich nicht bereits als abgeschlossen speichern.
6. App schließen und erneut öffnen. Termine und ihre Kundenverknüpfung bleiben erhalten.

Der lokale Kalender funktioniert vollständig ohne Google und ohne Internet. Einrichtungs- und Nutzungsdetails: [KALENDER.md](KALENDER.md).

**Google ist optional.** Ab 0.5.1 erfolgt die Verbindung über die bereits im Android-System eingerichteten Kalender. Android übernimmt den eigentlichen Google-Kontosync; ein Geräteabgleich ist keine Cloud-Bestätigung. Der bisherige OAuth-/Anmeldeserver-Prototyp ist nicht der aktive Android-Pfad. [Direkte Geräteverbindung](ANDROID-GERAETEKALENDER.md).

## Neu in 0.4.0

- Optionales Haarprofil mit Naturhaarfarbe, aktueller Farbe, Struktur, Eigenhaar-/Wunschlänge, Dichte, aktuell getragenen Extensions und individuellen Wünschen.
- Mehrere kundenbezogene Extensions-Positionen mit freien Herstellern, Arten, Farben und Farbcodes, Länge, Gewicht, zusätzlicher Anzahl, exakten Gesamtpreisen, Datum, Lieferstatus und Notizen.
- Anlegen, Bearbeiten und bestätigtes Löschen; Änderungen und gelöschte Positionsstände bleiben in der Kundenhistorie lesbar.
- Eigener Bereich **Extensions** in der unteren Navigation, Suche nach Kundin/Produkt und Filter nach Lieferstatus. Eigene vorhandene Angaben werden beim Erfassen vorgeschlagen.
- Logo, Farben und bisherige Gestaltung bleiben erhalten. Keine Haarlagerverwaltung und keine neuen Sicherungsfunktionen.

### Von einer älteren Testversion wechseln

Der Versionscode ist **4**. Die geprüfte Testsignatur unterscheidet sich von 0.5.0. Deshalb die alte Test-App deinstallieren und diese APK neu installieren. Dabei gehen lokale Testdaten verloren; dies ist für diese Entwicklungsphase ausdrücklich akzeptiert. Beim ersten Start wieder einen eigenen Zugang und bei Bedarf sechs fiktive Kundinnen anlegen. Wer die Daten behalten möchte, vorher eine `.haarvinci`-Sicherung an einem getrennten Ort erstellen. Keine echte Kundendaten in dieser Testversion verwenden.

### Die neuen Bereiche ausprobieren

1. Eine fiktive Kundin öffnen und **Bearbeiten → Ihr Haarprofil** aufklappen. Zum Beispiel „Dunkelblond“, „Wellig“, Eigenhaarlänge „25,5“ und Wunschlänge „50“ eintragen. Speichern und nach erneutem Öffnen prüfen.
2. In der Kundenakte **Extensions hinzufügen** wählen. Einen erfundenen Hersteller, eine Art, Farbe, Länge, Gewicht und den Gesamt-Einkaufspreis eintragen. Deutsche Kommawerte wie „149,90“ werden akzeptiert. Speichern.
3. Für dieselbe Kundin eine zweite Position mit anderer Farbe oder Länge anlegen.
4. Eine Position bearbeiten, anschließend die andere löschen und die Löschung bestätigen. Unter **Kundenhistorie** lassen sich Änderungen und der gelöschte Stand aufklappen.
5. Unten **Extensions** öffnen und nach der Kundin, einem Hersteller oder Farbcode suchen. Einen Lieferstatus filtern.
6. Die App schließen und wieder öffnen: Haarprofil und verbliebene Positionen bleiben gespeichert.

Die Extensions-Anzahl ist keine Besuchszahl; Bestelldatum und letzter tatsächlicher Besuch sind unterschiedliche Angaben. Besuchszahlen sind seit 0.5 an abgeschlossene Termine gebunden. Behandlungen und Zahlungen folgen später. Weitere fachliche Details: [EXTENSIONS.md](EXTENSIONS.md).

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
