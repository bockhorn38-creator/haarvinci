# HaarVinci Signature 1.1.0 – Änderungen und Medienstatus

**Stand: 12. November 2026. Noch kein vollständiger Galerieabschluss:** Das angekündigte neue ZIP beziehungsweise die acht importierbaren Galerie-JPGs fehlen. Textdateien und Bildvorschauen sind gesichtet. Es wird keine Integration oder Abnahme echter neuer Vorher-Nachher-Bilder behauptet. Die vorhandenen Reel-Standbilder bleiben in der laufenden Vorschau erhalten.

## Gestaltung und Bedienung

Die bestehende Astro-Website wurde gezielt weiterentwickelt. Zentrale Farben: Elfenbein `#F8F4ED`, Tiefschwarz `#211D1C`, Champagnergold `#B99A68`, Soft Rosé `#E7D4D0`, Warmgrau `#6C625D`; kleine Texte auf roséfarbenen Flächen erhalten einen dunkleren Kontrast. Grün `#147A43` kennzeichnet WhatsApp. Vorhandene Serif-/Sans-Serif-Schriften bleiben lokal.

Neue Reihenfolge und Bildrhythmik: Haarmotiv im Hero, frühe Ergebnisse, dunkler Vertrauensbereich, Leistungen, Methode und fünf Bestellschritte, echtes Conny-Porträt und Studio, Preise, neun plus zehn aufklappbare FAQ, Anfahrt und Kontakt. Keine erfundenen Leistungen oder Preise. Der bisherige KI-Gestaltungsentwurf ist unverändert erhalten, das echte zugrunde liegende Porträt trägt jetzt den Conny-Bereich mit HTML-Texten.

WhatsApp ist im angehefteten Header integriert, grün, mindestens 48 × 48 Pixel groß und auch ohne JavaScript sichtbar. Die aggressive Kollisionsprüfung und die zusätzliche frei über dem Inhalt liegende Ebene entfallen. Native Dialoge behalten ihre Fokusführung. Die mobile Navigation wird vor dem ersten sichtbaren Rendern auf ihren korrekten JavaScript-Zustand gesetzt, sodass eine langsam ladende Seitenlogik die Kopfzeile nicht nachträglich verkleinert. Ohne JavaScript bleibt die Navigation sichtbar.

Google-Bewertungen werden neutral über das Unternehmensprofil erreichbar; „Bewertung abgeben“ ist ein eigener Link. Die Presse-Karte verlinkt ausschließlich den gelieferten KN-Beitrag. Keine Zitate, Sternedurchschnitte, Artikelbilder, Gesundheitsgeschichten oder fremden Screenshots übernommen.

Anfahrt nennt ausdrücklich das 1. Obergeschoss und grenzt das Studio vom Imbiss unten ab. Ein Kundenstellplatz am Eichkamp steht nach Absprache zur Verfügung. Die genaue Zufahrt wird per WhatsApp angefragt; keine Stellplatznummer, Hofeinfahrt oder Parkplatz-Navigation erfunden.

## Medien und Rechte

| Material                                             | Einsatz                                                                    | Status                                                                                 |
| ---------------------------------------------------- | -------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| Vorhandene Reel-Frames aus 1.0.3                     | Hero, bisherige Ergebnisbilder, Behandlungsablauf und Conny bei der Arbeit | Aus dem bisherigen Vorschauprojekt übernommen; keine neuen Reel-Exporte oder Retuschen |
| `conny-portraet.jpg`                                 | Echtes Porträt im Conny-Bereich                                            | Bestehendes unverändertes Ausgangsbild, SHA-256 in `assets-source/HERKUNFT.json`       |
| `conny-gestaltungsentwurf.png`                       | Als bereits bestätigte gestalterische Quelle erhalten                      | Nicht als neue echte Szene ausgegeben                                                  |
| Vorhandene drei Studiofotos und schwarzer Schriftzug | Methode, Studio und Header                                                 | Unveränderte Quellen; dieselben SHA-256-Werte wie im neuen Übergabeverzeichnis         |
| Vier neue Vorher-Nachher-Paare                       | Separate private Galerie vorgesehen                                        | Acht JPGs fehlen; alle acht Website-Freigaben und Paarbestätigungen bleiben offen      |
| Google-Maps-, Review- und Pressescreenshots          | Nur zur Einordnung im Chat                                                 | Nicht importiert oder ausgeliefert                                                     |

`content/paired-results.json` enthält die vorgegebenen Zuordnungen und Originalprüfsummen. `npm run import:signature` akzeptiert nur die exakt passenden Originaldateien und ändert keine Einwilligung. Es schreibt nach `.private-media/`, niemals nach `public/`. `npm run build:private` erzeugt eine getrennte Vorschau unter `.private-preview/`; ungeklärte Fotos werden dort als optimierte WebP-Daten direkt in private HTML-Dateien eingebettet. Der normale Build filtert jedes Paar ohne beide Einzelfreigaben heraus, auch wenn globale Release-Schalter später freigegeben werden. Aktive private Bildvorschau blockiert einen öffentlichen Release. Astro erzwingt für private Builds einen Ausgabeordner unter `.private-preview/`, auch bei einem versehentlichen normalen Build-Aufruf. Abweichende CLI-Ziele und ein Export privater Builds in normale Downloadordner werden abgewiesen.

Die Galerie ist mit **fiktiven geometrischen Testflächen** über den tatsächlichen Import-/Build-/Offline-Pfad geprüft. Das ist ausdrücklich keine visuelle Abnahme der fehlenden Originalbilder. Alle Änderungen sind ohne Retusche, Generierung oder Manipulation von Haarergebnissen umgesetzt.

## Geänderte und neue Dateien

- `src/pages/index.astro`, `src/layouts/Layout.astro`: Inhalte, Reihenfolge, Navigation, FAQ und Originalporträt.
- `src/styles/global.css`, `src/styles/signature.css`: zentrale Tokens, responsive Premium-Gestaltung und Kontraste.
- `src/components/FloatingWhatsApp.astro`, `Contact.astro`, `Arrival.astro`, `Trust.astro`, `PairedResults.astro`: echte Kontakt-/Anfahrtsfunktionen, Verweise und Bildvergleich.
- `src/data/site.ts`, `paired-results.ts`, `publication.ts`, `content/paired-results.json`: bestätigte Quellen, einzeln geprüfte Bildfreigaben und private Ausgabe.
- `scripts/import-signature.mjs`, `build-private-preview.mjs`, `check-release.mjs`, `prepare-assets.mjs`, `export-preview.mjs`, `export-single-preview.mjs`: Import, getrennte Exporte, Metadatenbereinigung und Release-Schutz.
- `tests/signature.spec.ts`, `tests/version-1-additions.spec.ts`: neue Funktionen, privater Galeriepfad und an die ausdrücklich gewünschte Weiterentwicklung angepasste Bestandsprüfungen. Alle übrigen Tests bleiben erhalten.
- `package.json`, `package-lock.json`: Version 1.1.0 und zwei zusätzliche Skripte, unveränderte Paketabhängigkeiten.
- `astro.config.mjs`, `tsconfig.json`, `.gitignore`, `.prettierignore`, `AGENTS.md`: generierte Testberichte aus der Quellprüfung ausschließen, private Medien und Vorschauen von Git und Veröffentlichung trennen.
- `briefing/signature-1.1/`: neun unverändert abgelegte Übergabe-Textdateien; die acht im Prüfsummenverzeichnis enthaltenen Texte wurden verifiziert. Die Prüfsummendatei enthält selbst keinen eigenen Hash.
- `README.md`, `PRUEFUNG.md`, dieses Dokument: Bedienung, Prüfungen und offene Punkte.

Checkpoint vor Beginn: Git-Tag `checkpoint/website-1.0.3-vor-signature-1.1`. Eigener Quellzweig `website/signature-1.1`; Verwaltungs-App und ihre Zweige bleiben unberührt.
