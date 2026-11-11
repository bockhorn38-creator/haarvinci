# Zusatzauftrag zu Version 1.0 · Stand 1.0.1

Das bestehende Website-Projekt wurde gezielt ergänzt. Seitenstruktur, Preisangaben, Inhalte und bisherige Funktionen bleiben erhalten. Keine neue Website, kein Backend, keine Änderung der Verwaltungs-App oder an IONOS.

## 1. Freigegebener Conny-Entwurf

`src/pages/index.astro` verwendet im Bereich „Die Frau hinter HaarVinci“ jetzt den ausdrücklich freigegebenen `Ueber_Conny_Gestaltungsentwurf.png`. Die Originaldatei ist unverändert unter `assets-source/conny-gestaltungsentwurf.png` erhalten; Herkunft und Prüfsumme stehen in `assets-source/HERKUNFT.json`.

`scripts/prepare-assets.mjs` erzeugt daraus nur einen technischen Ausschnitt: links oben, **720 × 1200 Pixel**. So bleiben Connys Gesicht, Brille und Locken vollständig im Porträt; die bereits eingebauten Texte und das Logo im rechten Bildteil entfallen. Es wurde kein Gesicht retuschiert oder neu generiert. Die vorhandenen Texte stehen weiterhin als echte HTML-Elemente daneben. `src/styles/global.css` verhindert eine weitere Beschneidung durch CSS auf Smartphone und Desktop.

## 2. Mobiler WhatsApp-Kontakt

Neu: `src/components/FloatingWhatsApp.astro`, eingebunden in `src/layouts/Layout.astro`. Unterhalb von 700 Pixeln erscheint ein dezenter schwebender WhatsApp-Link im vorhandenen Rosé-/Goldstil. Ziel unverändert: `https://wa.me/4917631600586`. Touch-Fläche mindestens 48 Pixel, sichere Abstände und Berücksichtigung der Geräte-Safe-Area.

Der Kontakt blendet sich aus, wenn er Text, Bilder oder Bedienelemente überdecken würde. Er bleibt bei geöffnetem Menü, Foto-Dialog und Formulareingaben ausgeblendet; im Kontaktbereich sind bereits direkte Kontaktwege vorhanden. Ohne JavaScript bleibt ein normaler mobiler WhatsApp-Link am Seitenende. Auf dem Desktop wird kein zusätzlicher schwebender Kontakt angezeigt. Es werden keine Nachrichten automatisch versendet.

## 3. SEO, Social Preview und Favicon

- `src/data/site.ts` und `src/layouts/Layout.astro`: exakter Startseitentitel **„HaarVinci | Schonende Haarverlängerung & Haarverdichtung in Kiel“**, eigene Beschreibung sowie vollständige Open-Graph- und Twitter-Card-Angaben mit absoluten HTTPS-URLs, Bildtyp, Größen und Alternativtexten.
- `src/pages/404.astro`: eigenständige Beschreibung. Die Fehlerseite bleibt auch im späteren Freigabebuild `noindex` und erhält keinen irreführenden Canonical-Eintrag.
- `scripts/prepare-assets.mjs`: **1200 × 630 Pixel** großes PNG aus dem vorhandenen HaarVinci-Schriftzug auf Creme/Rosé/Gold. Kein neues KI-Bild. Ausgabe: `/social/haarvinci-vorschau-1.0.1.png`.
- Favicon aus dem vorhandenen runden HaarVinci-Markenemblem: eingebettetes SVG, PNG mit 32 und 48 Pixeln sowie Apple-Touch-Icon mit 180 Pixeln. Original: `assets-source/markenemblem.png`. Die bisherige frei gestaltete H-Initiale wurde ersetzt.
- `scripts/export-preview.mjs`: bindet auch PNG-/Apple-Icons in die eigenständige Vorschau ein, ohne neue Ressourcenabrufe zu benötigen.

Die Vorschau bleibt bewusst `noindex`, solange Rechtstexte und Freigabe für den eigentlichen Livegang fehlen. Echte Google-Indexierung und die Darstellung in einer tatsächlichen WhatsApp-Linkkarte können erst nach Auslieferung der Website unter der öffentlichen HTTPS-Adresse geprüft werden. Die Dateien und Metadaten wurden lokal vollständig geprüft; die Seite wurde nicht live geschaltet.

## Prüfung und Sicherung

**29 Browserprüfungen erfolgreich:** alle 18 bisherigen Prüfungen und 11 zusätzliche Prüfungen für Porträt, Metadaten, Bild-/Icondateien und mobilen WhatsApp-Kontakt. Neue Größen: Porträt bei 320/390/412/1440 Pixeln; WhatsApp bei 320×568, 360×640, 390×844, 412×915 und 600×800. Verifizierte Touch-Flächen, keine Inhaltsüberdeckung, Tastaturfokus, korrekter Link, ausgeblendeter Kontakt bei Menü/Foto/Formular sowie Axe-Prüfung des sichtbaren Kontakts. Bisherige Preise, Formular, Galerie, Navigation, Rechtsentwürfe und eingebettete Vorschau bestehen weiterhin.

`npm run check`, `npm run format:check`, statischer Build und Vorschau-Export werden ebenfalls geprüft. Eine tatsächliche WhatsApp-Nachricht wird im Test nicht versendet. Die Zuordnung zur installierten App und der direkte Doppelklick bleiben Prüfungen auf dem eigenen Gerät; die Cloud sperrt direkte `file://`-Navigation weiterhin.

Weitere angepasste Dateien: `AGENTS.md`, `.gitignore`, `.prettierignore`, `README.md`, `PRUEFUNG.md`, `THIRD_PARTY_NOTICES.md`, `package.json` und `package-lock.json`. Die Paketversion steigt auf **1.0.1**, ohne neue Abhängigkeiten. Die vorherige ZIP-Version 1.0.0 bleibt erhalten.
