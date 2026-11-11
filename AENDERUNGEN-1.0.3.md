# HaarVinci 1.0.3 – WhatsApp sofort sichtbar

## Korrektur

Der bisherige schwebende Kontakt war nur unter 700 Pixeln aktiv. Außerdem blendete ihn die Kollisionsprüfung aus, sobald er Text, Bilder oder Bedienelemente verdeckt hätte. Dadurch war er am PC vollständig und auf dem Smartphone häufig unsichtbar. Die bisherigen Prüfungen hatten nur nach einer sichtbaren Stelle beim Scrollen gesucht; die sofortige Erreichbarkeit wurde damit nicht ausreichend geprüft.

Die Kopfzeile enthält jetzt einen zusätzlichen direkten WhatsApp-Button, der auf Smartphone, Tablet und PC sofort sichtbar ist und beim Scrollen in der angehefteten Kopfzeile bleibt. Er liegt innerhalb des Layouts und verdeckt keine Seiteninhalte. Unter 400 Pixeln erscheint das erkennbare WhatsApp-Symbol mit zugänglichem Namen; ab 400 Pixeln zusätzlich der Text „WhatsApp“. Die Fläche ist mindestens 48 × 48 Pixel groß. Der Link funktioniert ohne JavaScript und öffnet `https://wa.me/4917631600586` erst nach bewusstem Anklicken.

Der bisherige mobile schwebende Kontakt mit Kollisionsschutz bleibt ergänzend erhalten. Inhalte, Bildauswahl, Preise, Design, Formulare und Verwaltungs-App werden dadurch nicht verändert.

## Geänderte Dateien

- `src/layouts/Layout.astro`: direkter WhatsApp-Kontakt in der gemeinsamen Kopfzeile aller Seiten.
- `src/components/Icon.astro`: lokal ausgegebenes WhatsApp-Symbol.
- `src/styles/global.css`: responsive Kopfzeile, Button und kompakte Darstellung auf kleinen Geräten.
- `tests/whatsapp-visibility.spec.ts`: sofortige Erreichbarkeit, Scrollen, Tastatur, korrektes Linkziel, kleine und große Displays, Betrieb ohne JavaScript und vollständig eingebettete HTML-Vorschau.
- `package.json`, `package-lock.json`: Version 1.0.3; Abhängigkeiten unverändert.
- `README.md`, `PRUEFUNG.md`, dieses Dokument: aktueller Prüf- und Bedienstand.

## Prüfung

Astro-/TypeScript-Prüfung, Formatierung, statischer Build und Offline-Export. Alle 32 bisherigen Browserprüfungen sowie acht neue WhatsApp-Prüfungen. Sofortige Sichtbarkeit bei 320, 390, 412, 760, 1100 und 1440 Pixeln; auch beim Scrollen zu Methode, Ergebnissen, Preisen, Conny und Kontakt. Sichtbarkeit in allen vier eingebetteten Vorschauseiten sowie ohne JavaScript auf Smartphone und PC. WhatsApp-Öffnung wird in Tests abgefangen; keine Nachricht wurde versendet.

Das Vorschau-ZIP erhält eine neue Versionsnummer; die alten Downloads bleiben erhalten. Der tatsächliche Aufruf der WhatsApp-App und der HTML-Doppelklick auf dem privaten Gerät bleiben manuelle Prüfungen. Kein Website-Livegang bei IONOS.
