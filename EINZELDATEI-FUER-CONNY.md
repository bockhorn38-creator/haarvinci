# Einzelne HTML-Datei für Conny

`HaarVinci-fuer-Conny.html` ist die bestehende Website-Vorschau auf Basis von Version 1.0.3 in einer einzigen Datei, etwa 3,5 MB groß. Kein ZIP, keine Installation und keine Begleitdateien erforderlich. Bilder, Gestaltung, Schriften einschließlich Lizenztexten und die vorhandenen Funktionen sind eingebettet. Der WhatsApp-Button bleibt in der Kopfzeile sichtbar.

Die Impressums- und Datenschutzentwürfe stehen in aufklappbaren Bereichen derselben Datei. Alle internen Links bleiben innerhalb der Datei. Es werden keine vollständigen Rechtsinhalte erfunden und keine bestehenden Freigabesperren aufgehoben. Der normale Webhosting-Build und die bisherigen ZIP-Downloads bleiben unverändert.

## Weitergeben

Die HTML-Datei auf dem eigenen Gerät speichern und in WhatsApp als **Dokument** anhängen. Conny lädt die Datei herunter und öffnet sie in einem Browser. WhatsApp zeigt HTML nicht selbst als Website an; je nach Android-Dateiverwaltung muss über „Öffnen mit“ ein Browser gewählt werden. Alternativ kann Conny die Datei auf einem PC öffnen. Die tatsächliche Dateizuordnung und Übertragung durch die private WhatsApp-App bleiben Prüfungen auf dem jeweiligen Gerät.

Der GitHub-Dateibereich stellt die Datei zum Speichern bereit. Der Raw-Endpunkt kann HTML als Quelltext anzeigen; das ist kein gehosteter Website-Aufruf. Auf der GitHub-Dateiseite den Download-Pfeil („Download raw file“) verwenden.

## Reproduzieren und prüfen

Nach einem vorhandenen aktuellen Vorschau-Build erzeugt `npm run export:preview` zusätzlich `offline-preview/HaarVinci-fuer-Conny.html`. Die neuen Skripte verändern ausschließlich die Exportdatei. `npm test` prüft auch diese Einzeldatei.

**43 Browserprüfungen erfolgreich:** die bisherigen 40 und drei zusätzliche Prüfungen für die Einzeldatei. Bilder, Menü, Preisnavigation, Studio-Großansicht, WhatsApp-Ziel, interne Links, eingebettete Schriftlizenzen und die Rechtsentwürfe sind geprüft. Die Einzeldatei lädt über erlaubtes lokales HTTP mit gesperrtem Netz ohne weitere Ressourcenabrufe. Auch ohne JavaScript bleibt sie bei 320 und 1440 Pixeln bedienbar.

Die Cloud sperrt direkte `file://`-Navigation. Der erfolgreiche Test des eingebetteten Inhalts wird deshalb nicht als tatsächlich ausgeführter Android-/Windows-Doppelklick oder WhatsApp-Versand ausgegeben. Keine Nachricht wurde versendet, kein Livegang bei IONOS durchgeführt.

Geändert beziehungsweise ergänzt: `scripts/export-preview.mjs`, `scripts/export-single-preview.mjs`, `tests/single-file.spec.ts`, `README.md`, `PRUEFUNG.md` und dieses Dokument. Die Verwaltungs-App wurde nicht verändert.
