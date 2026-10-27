# Haarvinci Android-Testversion 0.5.1

Die einzelne APK in diesem Zweig wurde unverändert aus dem erfolgreichen Android-Emulatortest 40604956787 übernommen. SHA256SUMS.txt und SIGNATUR.txt dokumentieren die geprüfte Originaldatei.

Neu: Native Android-Gerätekalender über CalendarContract, getrennte geschäftliche/private Kalender und ChatGPT-Textimport per Android-Teilen oder Zwischenablage. Importvorschau mit Pflichtfeldprüfung, ausdrücklicher Bestätigung und atomarer Speicherung; keine Lagerverwaltung. Kein eigener Server, keine Domain, kein Google-Cloud-Projekt und keine OpenAI-API erforderlich. Kundinnen, Haarprofile, Extensions, Historie und lokaler Kalender bleiben nutzbar.

Dokumentation im Hauptzweig: docs/CHATGPT-IMPORT.md und docs/ANDROID-GERAETEKALENDER.md. Native Provider-Testdaten und Android-Textübergabe sind im Emulator geprüft. Echte Google-Kontosynchronisierung und die genaue Text-/Link-Übergabe der installierten ChatGPT-App müssen noch auf dem Pixel getestet werden.

Testsignierung: die vorherige Testversion bei abweichender Signatur deinstallieren und diese APK frisch installieren. Bisherige lokale Testdaten gehen dabei verloren. Ausschließlich fiktive Daten verwenden. Keine automatische Gerätesynchronisierung.

Der separate Download-Zweig dient als Ersatz, weil die GitHub-Actions-Integration das Anlegen eines GitHub Releases mit HTTP 403 verweigert. Der Hauptzweig enthält ausschließlich Quellcode; die Repository-Sichtbarkeit wird nicht geändert.
