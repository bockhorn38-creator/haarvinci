# HaarVinci 1.0.2 – echte Reel-Standbilder

Die bestehende Website gezielt erweitert; Gestaltung, Seitenstruktur, Preise, Kontakte, freigegebenes Conny-Porträt, Studio-Galerie und Anfragehelfer bleiben erhalten. Keine Änderung an der Verwaltungs-App.

## Welche Reels wo verwendet werden

| Reel                                  | Zeitpunkt | Standbild                      | Website-Bereich                                                      |
| ------------------------------------- | --------- | ------------------------------ | -------------------------------------------------------------------- |
| `01_reel_extensions_rot.mp4`          | 00:00,0   | `reel-ergebnis-rot.png`        | Ergebnisse: rote Längen, glattes fertiges Finish der Eröffnungsszene |
| `03_reel_glanz_und_laenge.mp4`        | 00:12,0   | `reel-ergebnis-glanz.png`      | Ergebnisse: dunkles Haar und Glanz in Nahansicht                     |
| `02_reel_behandlung_und_ergebnis.mp4` | 00:13,8   | `reel-ablauf-ausgangslage.png` | Methode: Eigenhaar nach dem Entfernen der bisherigen Extensions      |
| `02_reel_behandlung_und_ergebnis.mp4` | 00:20,2   | `reel-ablauf-cornrows.png`     | Methode: geflochtene Cornrow-Basis                                   |
| `02_reel_behandlung_und_ergebnis.mp4` | 00:56,1   | `reel-ablauf-finish.png`       | Methode: Ausschnitt des fertigen Lockenstylings von hinten           |
| `02_reel_behandlung_und_ergebnis.mp4` | 00:54,0   | `reel-conny-beim-finish.png`   | Über Conny: echter Arbeitsmoment beim Finish                         |

**Reel 04 – konkrete Grenze:** `04_reel_conny_produkterklaerung.mp4` überschreitet die 32-MiB-Übertragungsgrenze und konnte nicht heruntergeladen oder im Original geprüft werden. Der im Chat sichtbare Kontaktbogen wurde zur Einordnung betrachtet; daraus wurde kein minderwertiges Website-Bild herauskopiert. Stattdessen ergänzt der echte Arbeitsmoment aus Reel 02 den Conny-Bereich. Für zusätzliche Produktberatungsbilder später eine komprimierte Datei oder einen kurzen Originalausschnitt unter 32 MiB bereitstellen.

Die drei verfügbaren Originalvideos wurden visuell über mehrere Zeitpunkte und ausgewählte Originalframes geprüft. Ungeeignete Szenen mit Speisen/Getränken, kundenseitigen Frontporträts, dunklen Übergängen oder starken Bewegungen wurden verworfen. Die zwei Ergebnisbilder sind einzelne echte Ergebnisse, kein Vorher-Nachher-Vergleich. Der erste Behandlungsschritt ist ausdrücklich die Situation nach dem Entfernen vorhandener Extensions; es wird keine gefilmte Beratung behauptet.

## Technische Umsetzung

- Sechs unretuschierte PNG-Standbilder mit 720 × 1280 Pixeln unter `assets-source/`. Keine Farbkorrektur, keine künstlichen Haarveränderungen, keine neue KI-Erzeugung.
- Ergebnisbilder in voller Höhe; die vier anderen Webmotive werden technisch auf die oberen 720 × 820 Pixel begrenzt. Eingebrannte Untertitel im unteren Bereich werden durch diesen Ausschnitt vermieden. HTML-Texte stehen separat. Bei Finish-Motiven zeigt der Ausschnitt einen Teil der Frisur; kein vollständiger Längenvergleich wird behauptet.
- Responsive WebP-Größen mit maximal 720 Pixel Breite, Lazy Loading, feste intrinsische Maße, Alternativtexte und lokale Auslieferung. Keine Hochskalierung, EXIF-/GPS-/XMP-Übernahme, Video-/Instagram-Anfragen oder neuen Dienste.
- Zwei Ergebnis-Karten, drei visuelle Behandlungsschritte im vorhandenen Methodenbereich und ein Arbeitsmotiv unter Connys Geschichte. Der bestehende fünfstufige Beratungs-/Bestellablauf bleibt vollständig erhalten. Ergebnis-Anker und Navigation werden durch echte Inhalte aktiviert.
- Herkunftsdatei enthält SHA-256 des Originalvideos und jedes exportierten PNGs sowie Zeitposition und FFmpeg-Version. Auswahl und Webausschnitte sind in `REEL-AUSWAHL.json` nachvollziehbar. Optionaler erneuter Export über `scripts/export-reel-stills.mjs`; Standardinstallation und Build benötigen keine Videos und kein FFmpeg.
- Rohvideos werden weder in `dist/` noch im Vorschau-ZIP oder Git gesichert. Exportierte Quellen, Herkunft und optimierte Webbilder sind im Paket enthalten. Frühere Download-ZIPs bleiben erhalten.

## Geänderte und neue Dateien

- `src/pages/index.astro`, `src/data/results.ts`, `src/styles/global.css`: Integration und responsive Gestaltung.
- `assets-source/reel-*.png`, `REEL-AUSWAHL.json`, `HERKUNFT.json`: sechs exportierte Originalframes und Herkunft.
- `scripts/export-reel-stills.mjs`, `scripts/prepare-assets.mjs`: nachvollziehbarer optionaler Export und optimierte Auslieferung.
- `tests/reels.spec.ts`, `tests/website.spec.ts`, `tests/version-1-additions.spec.ts`: Prüfungen der neuen Motive und aktivierten Ergebnis-Navigation; bestehende Tests bleiben erhalten.
- `package.json`, `package-lock.json`: Versionsnummer 1.0.2, unveränderte Abhängigkeiten.
- `README.md`, `AGENTS.md`, `PRUEFUNG.md`, `THIRD_PARTY_NOTICES.md`, dieses Dokument und `briefing/03_CODEX_ZUSATZAUFTRAG_REELS.md`: Bedienung, Herkunft und Prüfstand.
- Generiert: responsive Dateien unter `public/medien/`, `src/data/media.json`, `dist/`, `offline-preview/`; nicht als generierte Dateien in Git aufgenommen.

## Prüfung und verbleibende Punkte

Die konkreten ausgeführten Prüfungen stehen in [PRUEFUNG.md](PRUEFUNG.md). Das Paket bleibt eine Website-Vorschau; kein Livegang bei IONOS. Vollständige Rechtsinhalte und finale Livefreigaben fehlen weiterhin. Reel 04 bleibt für eine spätere Ergänzung offen. Die Verwaltungs-App und Android-APK sind von diesem Website-Auftrag nicht betroffen.
