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

Windows-Prüfung bestätigt: [Workflow-Lauf 40419706517](https://github.com/bockhorn38-creator/haarvinci/actions/runs/40419706517), Quellstand `33046f76589da52f283e9f88a055e3cd36db3adc`, Ergebnis **success**. Die Windows-Tests, Programmbau, deutscher Inno-Setup-Installer, tatsächliche Installation und Funktionsprüfung des installierten Programms wurden erfolgreich abgeschlossen. Das Artefakt `Haarvinci-Windows-Installer` enthält Setup und SHA-256-Prüfsumme. Ein erster Windows-Test hatte noch offene SQLite-Testverbindungen aufgedeckt; nach explizitem Schließen bestehen die Prüfungen auch auf Windows. Die physische Maschine der Benutzerin wurde nicht geprüft.

## Android-Test-APK 0.3

Bestätigter erfolgreicher [Workflow-Lauf 40429678795](https://github.com/bockhorn38-creator/haarvinci/actions/runs/40429678795), Quellstand `c4cc09901adbb2e583bf23deb2e27185d6a8b81f`.

- 31 gemeinsame Django-Prüfungen bestanden; Android-Kern zusätzlich isoliert mit tatsächlicher Sicherung/Rückspielung und Keep-Alive-Abbruch geprüft.
- Universelles APK für arm64-v8a und x86_64 mit gepinnten Python-Paketen und Paket-Hashes gebaut. Java-Prüfung der lokalen Herkunftsbeschränkung bestanden.
- Dieselbe gebaute APK auf dem Pixel-6-Emulator unter Android 15 installiert.
- Ersteinrichtung, privater Cookie-Zugangsschutz, Kundenanlage, Bearbeiten, Neuladen, Suche, echte Android-Dateiauswahl, vollständige Sicherung, Rückspielung mit zusätzlicher Sicherung des vorherigen Stands und erneute Anmeldung geprüft. Der vollständige instrumentierte Ablauf führte einen Test aus und bestand.
- Anschließend den App-Prozess tatsächlich mit Android beendet. Ein zweiter instrumentierter Test startete die App erneut, meldete sich an und fand die gespeicherte Kundin wieder. Auch dieser Test führte einen Test aus und bestand.
- APK mit apksigner verifiziert; APK, SHA-256-Prüfsumme und Zertifikatsinformationen als Artefakt `Haarvinci-Android-Test-APK` bereitgestellt.
- Entwicklungssignierung für eine Testversion; keine Play-Store-Veröffentlichung, keine dauerhaft verwaltete Freigabesignierung und kein Test auf Connys physischem Pixel behauptet.

### Direkter Release-Download, 27. Oktober 2026

Die vorhandene APK wurde im erfolgreichen [Übertragungslauf 40470816019](https://github.com/bockhorn38-creator/haarvinci/actions/runs/40470816019) aus dem ursprünglichen Artefakt übernommen und als einzelne Datei im [Testrelease android-test-v0.3.0](https://github.com/bockhorn38-creator/haarvinci/releases/tag/android-test-v0.3.0) veröffentlicht. Kein erneuter Build, keine neue Signierung. Ursprünglicher erfolgreicher Testlauf, Quellcommit, APK-Prüfsumme, Zertifikatsausgabe und Paketidentität wurden vor der Veröffentlichung geprüft.

Der vollständige direkte APK-Download wurde anschließend ohne Anmeldung durchgeführt: 52.035.753 Bytes, SHA-256 `c0aa2abce23512555fa3ef95d6d2f74bfe53cd733cfff811dd381f4548f96db4`. Die Prüfsumme stimmt mit dem von GitHub ausgewiesenen Release-Asset-Digest überein. Die Repository-Sichtbarkeit wurde nicht geändert; GitHub meldete das Repository bereits vor der Veröffentlichung als öffentlich.

## Haarprofile und Extensions – Android 0.4.0

Geprüfter Android-Quellstand `711b6c9e6d570efef7097ae90778444163928076`, erfolgreicher [Android-Prüflauf 40562980839](https://github.com/bockhorn38-creator/haarvinci/actions/runs/40562980839).

- 48 automatisierte Django-Prüfungen auf PostgreSQL und erneut auf dem tatsächlichen SQLite-Profil bestanden. Darunter optionale Haarprofile, deutsche Kommawerte, mehrere Positionen, exakte Preise, Pflichtfelder/Grenzen, Datenbank-Constraints, Eigentümer-/Kundenzuordnung, Anmeldung/CSRF, Versionskonflikte bei Änderung und Löschung, chronologische Historie, atomare Speicherung, Export und HTML-Escaping.
- Bisheriger Chromium-Kundenablauf und zusätzlicher realer Oberflächenablauf für Haarprofile/Extensions bestanden: Anlage, ungültiger Preis mit Eingabeerhalt, Korrektur, mehrere Positionen, Bearbeitung, bestätigte Löschung, Historie, Eingabevorschläge, Suche/Filter und Export. Neue Seiten bei 360, 390, 412, 600, 760, 1024 und 1440 Pixeln ohne horizontalen Überlauf. Bildschirmfotos mit dem bisherigen Design visuell kontrolliert; ausschließlich fiktive Daten.
- Android-Python-Kern mit privatem Cookie, Haarprofil und Extensions sowie vorhandener Sicherung/Rückspielung in einem isolierten temporären Ordner erfolgreich geprüft.
- APK im Pixel-6-Emulator unter Android 15 installiert. Vollständiger instrumentierter Ablauf mit Haarprofil, zwei Extensions-Positionen, serverseitiger Fehlerkorrektur, Bearbeitung, bestätigter Löschung, Historie und gefilterter Übersicht bestanden. Die vorhandene Android-Dateiauswahl/Sicherung/Rückspielung wurde mit den neuen Daten erfolgreich geprüft.
- Anschließend echten Android-App-Prozess beendet und in einem zweiten instrumentierten Test erneut gestartet: Kundin und Extensions mit ursprünglicher Farbe und exaktem Preis wiedergefunden. Das Skript verlangt ausdrücklich `OK (1 test)` für beide separaten Abläufe.
- APK-Signatur und Paketidentität geprüft: `de.haarvinci.app.preview`, Versionscode 2, Version 0.4.0. Die Testsignatur unterscheidet sich nachweislich von 0.3.0; deshalb ist auf einem bereits mit 0.3.0 belegten Gerät eine Neuinstallation erforderlich. Kein Test auf dem physischen Pixel behauptet.
- Auch das native Qt-Fenster mit dem gemeinsamen Kern lokal erfolgreich geprüft. Der Wiederherstellungstest verändert nun einen vorhandenen Datensatz, statt durch rohe Kundenlöschung neue Historienverknüpfungen zu beschädigen. Dies ist eine Korrektur des Testablaufs; keine zusätzliche Sicherungsfunktion.

### Bereitstellung der Original-APK

GitHub hat das gewünschte Release zweimal mit `HTTP 403: Resource not accessible by integration` für das Anlegen eines Releases verweigert. Die Berechtigungen und die Repository-Sichtbarkeit wurden nicht verändert. Als Ersatz hat [Bereitstellungslauf 40564549039](https://github.com/bockhorn38-creator/haarvinci/actions/runs/40564549039) genau die bereits geprüfte APK in einen separaten Download-Zweig übernommen, ohne sie neu zu bauen oder zu signieren. Der Hauptzweig enthält keine APK-Binärdatei.

[Direkte APK-Datei](https://github.com/bockhorn38-creator/haarvinci/raw/refs/heads/android-test-downloads/Haarvinci-Android-Test-0.4.0.apk), Download-Commit `3264344e87b38aece110bebf159e07a57e61efb5`, 52.077.225 Bytes. SHA-256: `26600009722b96bd12b7767b9e372169b1bf032a7af874b2a9fef20e00df1eb8`.

Der vollständige direkte Download ohne Anmeldung wurde sowohl vom Bereitstellungsworkflow als auch anschließend aus der Cloud ausgeführt und mit der originalen APK-Prüfsumme verglichen. Das separate GitHub Release bleibt wegen der Integrationsberechtigung offen; der Einzeldatei-Download ist nutzbar.

Windows-Kompatibilität abschließend bestätigt: [Workflow 40564140644](https://github.com/bockhorn38-creator/haarvinci/actions/runs/40564140644), Quellstand `57b0b4c`. Alle 48 Prüfungen, Programmpaket einschließlich des neuen Moduls/Migrationen, deutscher Installer, tatsächliche Installation und Funktionsprüfung des installierten Programms erfolgreich. Der einzige zusätzliche Code gegenüber dem getesteten Android-Stand betrifft den Desktop-Testablauf und die Bereitstellung; der Android-Anwendungskern blieb unverändert.

## Kalender und Termine – Android 0.5.0

Geprüfter Android-Quellstand `3d73d102634e7345d2f5d190e632df2f5a371f66`, erfolgreicher [Android-Lauf 40583235626](https://github.com/bockhorn38-creator/haarvinci/actions/runs/40583235626). Der frühere erste 0.5-Lauf `40582030777` bestand ebenfalls; ausgeliefert wird der abschließende Stand mit zusätzlicher Rollen-/Sommerzeit-/Outboxabsicherung.

- **98 automatisierte Django-Prüfungen auf PostgreSQL und erneut auf dem tatsächlichen SQLite-Profil bestanden.** Neue Abdeckung: Terminanlage, Bearbeitung/Verschieben, Absage, echte abgeschlossene Besuche, nächste/letzte Termine, Eigentümer-/Kunden-/Terminartgrenzen, Anmeldung/CSRF, Versionen, Datenbanktransaktionen, alle Ansichten und Zeitnavigation, Puffer-/Belegungskonflikte und ausdrückliche Bestätigung, Sommer-/Winterzeit einschließlich eines Puffers über die Zeitumstellung.
- Zusätzlicher echter Chromium-Ablauf mit fiktiven Daten bestanden: Live-Dauer, Verschieben, Pufferwarnung, Konfliktbestätigung, Absage, abgeschlossener Besuch, Kundenverknüpfung, Tag/Woche/Monat und nicht eingerichtete Google-Verbindung. Neue Seiten bei sieben Bildschirmbreiten von 360 bis 1440 Pixeln ohne horizontalen Überlauf; Screenshots visuell mit dem bestehenden Design kontrolliert. Abschließender Lauf mit frisch gestartetem Server erfolgreich.
- Google-API und Anmeldedienst automatisiert **mit simulierten Antworten** geprüft: feste IDs, unklarer Insert-Ausgang ohne Duplikat, abweichender Vergleichsstand als Konflikt, Übernahme von Änderungen/Absagen, beidseitige Änderungen, ETag-412, explizite Konfliktentscheidungen, alte Entscheidungen, Schutz fremder Ereignisse, paginierter Abruf, private Datenminimierung, fehlendes Internet/erhaltener Cache, Trennung der Rollen und Tokenablage außerhalb der Datenbank.
- OAuth-Bibliothek erzeugt State und PKCE; verschlüsselte Übergabe mit falschem State/Beweis, Ablauf, Ablehnung, einmaligem Abruf sowie gerätegebundener Erneuerung/Trennung geprüft. Dies ersetzt keine echte Google-Anmeldung oder Berechtigungsabnahme.
- **APK tatsächlich auf Pixel-6-Emulator / Android 15 installiert.** Vollständiger instrumentierter Ablauf mit Kundenverwaltung/Haarprofil/Extensions und anschließend Kalender: Anlegen, Dauer, Verschieben, Pufferkonflikt, ausdrückliche Übernahme, Absagen, vergangener abgeschlossener Besuch, Kundenübersicht und alle drei Kalenderansichten bestanden.
- Android Keystore/AES-GCM auf dem Emulator tatsächlich geprüft: Tokenwert entschlüsselbar, gespeicherter Umschlag ohne Klartext, Kopie in eine andere Kontobindung wird abgewiesen. Keine echten Tokens verwendet.
- Vorhandene Sicherung/Rückspielung mit Terminen ausgeführt; ursprüngliche Terminzeit nach Rückspielung bestätigt. Anschließend App-Prozess beendet und in einem zweiten instrumentierten Test Kundin, Extensions sowie Terminzeiten/Absage wiedergefunden. Beide separaten Tests mussten tatsächlich `OK (1 test)` ausweisen.
- Paket `de.haarvinci.app.preview`, Versionscode **3**, Version **0.5.0**, Signatur mit apksigner geprüft. Signatur gegenüber 0.4.0 nachweislich abweichend: Neuinstallation nötig, bisherige lokale Testdaten gehen verloren.
- **Windows-Kompatibilität:** [Workflow 40583236996](https://github.com/bockhorn38-creator/haarvinci/actions/runs/40583236996) am selben Anwendungskern erfolgreich: 98 Prüfungen, Programmbau/Installer und tatsächlich installiertes Programm geprüft.
- Ruff, Formatierung, Migrationsprüfung und Sicherheitsprüfung des produktiven Serverprofils ohne Fehler bestanden. Keine zusätzliche Sicherungsfunktion oder Behandlungs-/Zahlungsmodule entwickelt.

### Direkte APK-Bereitstellung 0.5

[Veröffentlichungslauf 40584901872](https://github.com/bockhorn38-creator/haarvinci/actions/runs/40584901872) hat die Originaldatei des geprüften Builds ohne Neubau/Neusignierung in den bestehenden Download-Zweig übernommen. Alte APKs und ihre Prüfsummen wurden erhalten; nur neue Versionsdateien ergänzt. Repository-Sichtbarkeit unverändert.

**[Einzelne APK direkt herunterladen](https://github.com/bockhorn38-creator/haarvinci/raw/refs/heads/android-test-downloads/Haarvinci-Android-Test-0.5.0.apk)** – 54.734.950 Bytes. SHA-256: `b0eb5e2fa1b0ae6c0282739294bfa0d3ebc954db7604f307ee9e4d8586439473`. Download-Commit `0ee5935c1a3f06a7cd42b86c9149814695b3bae7`; Signatur/Prüfsumme im Unterordner `0.5.0`. Der anonyme vollständige Download wurde im Bereitstellungsworkflow und anschließend aus der Cloud durchgeführt und per Prüfsumme mit der getesteten Originaldatei verglichen.

**Offen für die tatsächliche Google-Verbindung:** eigenes Google-Cloud-Projekt/Calendar-API-Freigabe, OAuth-Webclient/Testnutzer, eigener vertrauenswürdiger HTTPS-Anmeldedienst mit privaten Schlüsseln, Auswahl der echten Kalender und Konto-/Berechtigungs-/Offlineabgleich nach docs/GOOGLE-KALENDER.md. Keine echten Google-Konten, echten Kundendaten oder Connys physisches Pixel wurden geprüft; kein Hosting wurde gebucht oder veröffentlicht.

## Android 0.5.1 – Gerätekalender und ChatGPT-Textimport

Prüfung am **28. Oktober 2026**, ausschließlich fiktive Daten. Anwendungskern/Android-Quellen: `dc14d9f137aea73a2f8146634018dfad51e8daab`.

- **124 Django-Tests auf PostgreSQL und SQLite bestanden**: bestehende Kunden-, Haarprofil-, Extensions-, Historien- und Kalenderabläufe; zusätzlich striktes versioniertes Importformat, Pflichtfelder/Unicode/unerlaubte Daten, manuelle eigentümerbegrenzte Kundenzuordnung, sitzungsgebundene RAM-Entwürfe, falsche Bestätigung, atomare Übernahme, gleichzeitige Bearbeitung, Dubletten/Wiederholung, überschneidende Termine und Zeitumstellung.
- Geräteabgleich mit simuliertem Provider: dauerhafte Schreibabsicht, wiederholter Abgleich ohne Kopien, lokale/entfernte Änderungen, beidseitiger Konflikt mit Versions-/Entscheidungsprüfung, Kundenumbenennung, Absage/Reaktivierung, unklare Inserts, fehlende/verschobene/mehrfach zugeordnete/wiederkehrende Ereignisse, Berechtigungsverlust, unveränderliche private Zeitdaten und stabile fremde Terminlinks.
- **Echte Chromium-Oberfläche**: Bestandsfunktionen Kunden/Extensions/Kalender und neuer Import geprüft. Link-Hinweis, fehlendes Pflichtfeld, Korrektur, Vorschauen ohne Fachdaten-Speicherung, ausdrückliche Bestätigung, zusammengehörige Kundin/Extensions/Termin und erneuter Import ohne Dubletten. Sieben Bildschirmbreiten einschließlich Pixel; kein horizontaler Überlauf. Deutsche Dezimal-/Datumsdarstellung und Gestaltung kontrolliert.
- **Android-Emulator, API 35 / Pixel 6**: [vollständig erfolgreicher Lauf 40604956787](https://github.com/bockhorn38-creator/haarvinci/actions/runs/40604956787). Die APK und Instrumentierung wurden installiert. Fünf separate instrumentierte Prüfungen mussten jeweils tatsächlich `OK (1 test)` ergeben: gesamter bestehender Ablauf einschließlich Dateiauswahl/Sicherung/Rückspielung; Bestandsdaten nach Prozessneustart; echter Calendar Provider; Provider-Verknüpfungen nach zusätzlichem Prozessneustart; nativer Teilen-/Zwischenablageimport.
- **Echter Calendar Provider** mit isolierten fiktiven LOCAL-Kalendern aus unterschiedlichen Testkonten: Berechtigung zunächst verweigert, anschließend erteilt; Auswahl beschreibbarer Kalender/readonly-Ausschluss, Kalenderfingerabdruck, markerbasierte Anlage ohne Kopien, Vergleich-vor-Schreiben bei externer Änderung, Update und Absage, verlorene Marker, Wiederfinden über die Beschreibung, fremde Ereignisse unverändert, private Wiederholungen über Sommerzeit und Ganztagsgrenzen. Private Abfrageprojektion tatsächlich auf `begin,end,allDay` geprüft; keine privaten Titel in der Antwort. Mehrfachmarker und Verschieben in den privaten Kalender stoppen Änderungen; dort nur ID-/Kalender-ID-Metadaten gelesen.
- Der **vollständige native Python-Ausgangskorb gegen den tatsächlichen Provider** wurde ausgeführt: zwei Rollen, lokale Anlage/Änderung/Absage, private Zeitdaten, wiederholte Abgleiche und unveränderte Verknüpfung nach `am force-stop` und neuem App-Prozess. Keine Sync-Adapter-Flags im Produktionscode; nur die Testfixture erzeugt LOCAL-Testkalender mit Adapterzugang.
- **Android-Textimport**: registrierter ACTION_SEND-Empfänger mit text/plain, Anmeldung vor Vorschau, echte erneute Android-Intent-Zustellung an eine laufende App, Zwischenablage über bewusste Programmmenüaktion, keine Anlage vor Bestätigung, zusammengehörige Einträge, Wiederholung mit gleicher Kennung, fehlende Felder und reiner ChatGPT-Link mit Kopierhinweis. Keine angemeldete ChatGPT-App vorausgesetzt oder als getestet ausgegeben.
- **Windows-Kompatibilität**: [erfolgreicher Lauf 40604956855](https://github.com/bockhorn38-creator/haarvinci/actions/runs/40604956855) auf demselben Anwendungskern: 124 SQLite-Tests, eingefrorenes Programm und Installer gebaut, tatsächlich installiert und Oberfläche/Speicherung/Sicherung/Rückspielung geprüft. Zusätzlich native Linux-Desktop-App und eingefrorenes Linux-Paket erfolgreich geprüft.
- Ruff, Formatierung, offene Migrationen und Sicherheitsprüfung des Produktionsprofils ohne Fehler. Android-Python-Kern mit privatem Zugang, Einrichtung, Speichern und echter Sicherung/Rückspielung bestanden. Version **0.5.1**, Versionscode **4**, Paket `de.haarvinci.app.preview`, Entwicklungssignatur durch apksigner geprüft.

**Noch nicht geprüft:** tatsächliche Google-Kontosynchronisierung auf einem physischen Pixel, Energieverwaltung dieses Geräts und die konkrete Text-/Link-Aktion einer dort angemeldeten aktuellen ChatGPT-App. Die direkten Android-APIs, nicht die Google-Cloud, wurden im Emulator geprüft. Pixel-Prüflisten: [Gerätekalender](ANDROID-GERAETEKALENDER.md), [ChatGPT-Import](CHATGPT-IMPORT.md). Kein eigener Server, kein Google-Cloud-Projekt und keine OpenAI-API eingerichtet oder erforderlich.

### Direkte Bereitstellung 0.5.1

[Veröffentlichungslauf 40605718260](https://github.com/bockhorn38-creator/haarvinci/actions/runs/40605718260) erfolgreich. Das Original aus dem vollständig erfolgreichen Android-Lauf wurde ohne Neubau oder Neusignierung im bestehenden Download-Zweig ergänzt. Download-Commit: `ac59543b6f8f4f13e648a0cfcd9cff5ace926542`. Bisherige APKs und Prüfsummen bleiben erhalten, Repository-Sichtbarkeit unverändert.

**[Einzelne APK 0.5.1 direkt herunterladen](https://github.com/bockhorn38-creator/haarvinci/raw/refs/heads/android-test-downloads/Haarvinci-Android-Test-0.5.1.apk)** – **54.824.741 Bytes**, SHA-256 `eddc63675f7e0b0b197e67034fe89cbf478400381a32ac0aeac7431901712879`. Der anonyme vollständige Download wurde im Veröffentlichungsworkflow und anschließend nochmals aus der Entwicklungsumgebung geprüft; Prüfsumme identisch. Signaturinformationen und Prüfsumme im Unterordner `0.5.1` des Download-Zweigs.

Zertifikat SHA-256: `e62d470103e9fdd83b02414ab54abd1f65d28c46cc388601350a2854f9dfc41a`. Gegenüber 0.5.0 nachweislich abweichend: Neuinstallation erforderlich, bisherige lokale Testdaten gehen bei Deinstallation verloren. Ausschließlich fiktive Daten verwenden.
