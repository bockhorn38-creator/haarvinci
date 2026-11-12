# HaarVinci Signature 1.1.0 – Prüfstand

Stand: **12. November 2026**. Bestehende Astro-Website gezielt erweitert. Kein Livegang und keine Änderungen an Android-/Windows-/Django-App, IONOS, Domain, DNS oder E-Mail.

**Offen:** Das neue Bild-ZIP beziehungsweise die acht zugeschnittenen Galerie-JPGs liegen nicht als importierbare Dateien vor. Bildvorschauen im Chat sind gesichtet, aber keine Originalbildintegration oder visuelle Abnahme der vier neuen Paare behauptet. Der tatsächliche private Import stoppt mit einer Liste der acht fehlenden Dateien. Der Galeriepfad ist ausschließlich mit ausdrücklich fiktiven Testflächen funktional geprüft.

## Erfolgreiche technische Prüfungen

- Astro-/TypeScript-Check für 30 Dateien ohne Fehler, Warnungen oder Hinweise. Generierte Playwright-Berichte sind aus der Quellprüfung ausgeschlossen. Prettier und Git-Diff-Prüfung erfolgreich.
- **51 Chromium-/Playwright-Prüfungen:** sämtliche bisherigen 43 Prüfungen, an die ausdrücklich gewünschte Weiterentwicklung angepasste Porträt-/WhatsApp-Prüfungen und acht Signature-Prüfungen. Der tatsächliche statische Build und die tatsächlichen HTML-Exportdateien werden geprüft, keine Ersatzoberfläche.
- Statischer Build mit Startseite, Impressums- und Datenschutzentwürfen sowie 404. Bestehende Preise, Haarmaterial-Vorauszahlung, fünf Bestellschritte, Weaving-Methode samt möglichen Mikroringen am Cornrow-Ende und Pflege-/Fremdhaarabgrenzungen erhalten.
- Ergebnisbereich früh vor Leistungen; Google-Profil und Bewertungsabgabe korrekt getrennt. Presse verweist nur auf die gelieferte KN-URL. Keine fremden Screenshot-Bilder, Sternebehauptungen, übernommenen Bewertungen oder Heilversprechen.
- Anfahrt nennt bestätigte Adresse und 1. Obergeschoss, grenzt den Imbiss im Erdgeschoss ab und verwendet ausschließlich die bestätigte Studio-Route. Parkplatzbutton bereitet eine WhatsApp-Anfrage zur genauen Zufahrt/Stellplatzinformation vor. Keine konkrete unbekannte Parkroute und kein erfundener Park-Pin.
- WhatsApp: sofort sichtbarer grüner Headerkontakt, mindestens 48 × 48 Pixel, auch ohne JavaScript. Sichtbarkeit beim Scrollen und am Seitenende; eigener Schwerpunkt bei 360, 390, 412 und 768 Pixeln. Kein über Formularen oder Fließtext schwebendes Zweitelement. Native Foto-Dialoge mit Escape, Fokus und Fokusrückgabe erhalten.
- Die mobile Kopfzeile bleibt auch bei gezielt verzögertem Seiten-JavaScript in gleicher Höhe; das Menü ist von Beginn an eingeklappt und funktioniert nach Laden der Ereignisbehandlung. Ohne JavaScript bleibt die sichtbare Navigation erhalten. Ein Regressionstest kontrolliert diesen Ladepfad.
- Responsive Bestandsprüfungen bei 320 bis 1440 Pixeln. Neue private Side-by-Side-Galerie mit fiktiven Testflächen bei 360, 390, 412, 430 und 1440 Pixeln: Vorher/Nachher gleichzeitig sichtbar, Bildverhältnisse erhalten, kein horizontaler Überlauf und keine Bild-EXIF-Metadaten in der Ausgabe.
- Neun FAQ zunächst direkt erreichbar; zehn weitere über ein natives Details-Element. Alle 19 Antworten bleiben erhalten und bedienbar.
- **Axe ohne Befunde** im geprüften WCAG-2-A/AA- und 2.1-A/AA-Regelsatz für Hauptseite, geöffnetes mobiles Menü und Rechtsentwürfe. Dabei entdeckte Kontrastfehler auf roséfarbenen Flächen sind korrigiert. Keine Behauptung einer vollständigen rechtlichen Barrierefreiheitszertifizierung.
- Anfragehelfer, Pflichtfeldfehler, Unicode/URL-Kodierung, WhatsApp-/E-Mail-Ziel, keine Speicherung und keine Erfolgstäuschung geprüft. Alle Formular-Testdaten sind fiktiv; keine echten Nachrichten gesendet.
- Keine Tracker, Iframes, extern geladenen Schriften, Cookies, LocalStorage oder SessionStorage. Inhaltsbilder haben Größenangaben und Alternativtexte, responsive WebP-Ausgabe ohne private Metadaten, Lazy Loading außerhalb des Heroes. Originalprüfsummen bleiben erhalten; keine KI-Retusche von Haarergebnissen.
- Mehrdatei- und Einzeldatei-HTML-Vorschau funktionieren mit vollständig gesperrtem Netz über lokal erfüllte Dokumentantworten. Keine weiteren Bild-, Schrift- oder Skriptabrufe. Einzeldatei unter 5 MB samt eingebetteter Schriftlizenzen, Kontakt und Rechtsentwürfen.

## Datenschutzpfad der neuen Galerie

Ein isoliertes temporäres Testprojekt verwendet acht geometrische JPEG-Testflächen mit fiktiven Metadaten, keine echten neuen Kundinnenfotos. Es prüft den Originalimport mit SHA-256-Kontrolle, lehnt manipulierte Dateien ab und lässt bereits geprüfte Privatkopien dabei unverändert. Die private Ausgabe landet ausschließlich unter `.private-preview/`. Anschließend erzeugt dasselbe Testprojekt einen normalen Build: ungeklärte Paare sind daraus ausgeschlossen, nach `public/medien/` wurde kein neues Kundenfoto geschrieben. Abweichende CLI-Ausgabeziele für private Builds und ein Export privater Bilder in den normalen Downloadordner werden nachweislich blockiert. Der eigentliche Freigabekatalog bleibt unverändert.

Alle vier Paare haben weiterhin `websiteApproved: false` und `pairConfirmed: false`. Alle fünf globalen Schalter in `content/release.json` bleiben `false`. Private Bildvorschau und öffentlicher Release blockieren einander technisch. Der positive Release-Test läuft nur mit technischen Rechtstextmarkern in einem getrennten temporären Projekt; keine Marker gelangen in die gelieferten Vorschauen. `noindex` wird ausdrücklich nicht als Datenschutz-Zugriffsschutz verwendet.

## Visuelle und lokale Ladebeobachtung

Vollständige Screenshots bei 390, 412 und 1440 Pixeln; ergänzende Ansichten von Ergebnissen, Vertrauen, Conny und Anfahrt. Kontrolliert wurden Lesbarkeit, Header, ganze Haarbilder, Kontraste, Inhalte und Kontaktaktionen.

Eine lokale Chromium-Beobachtung der ersten Ansicht ergab rund 229–284 KB übertragene Ressourcen. Ein zusätzlich beobachteter Sprung der mobilen Kopfzeile bei langsamer JavaScript-Ausführung wurde korrigiert und durch einen Regressionstest abgesichert. Diese Werte stammen aus der Cloud mit lokalem HTTP, sind keine Lighthouse-Bewertung, kein mobiler Netzwerktest und keine zugesicherten Pixel-Leistungswerte. Die tatsächlichen Messdaten liegen den Ansichten bei.

## Reproduzieren

```bash
npm run check
npm run format:check
npm run build
npm run export:preview
npm test
```

Für die echte neue Galerie zusätzlich zuerst `npm run import:signature -- PFAD_ZUM_ENTPACKTEN_UEBERGABEORDNER`, danach `npm run build:private`. Dieser Ablauf benötigt die fehlenden Original-JPGs und schreibt keine Freigabe automatisch um.

## Grenzen und offene Abnahme

- Neues ZIP und die acht Original-JPGs fehlen. Neue Bildpaarungen und konkrete Kundinnenfreigaben sind noch durch Conny zu bestätigen; insbesondere Goldblond/„Ohne extensions“ nicht ohne Einordnung als freigegebene Behandlungsgeschichte veröffentlichen.
- Der Cloud-Browser sperrt direkte `file://`-Navigation. Windows-Doppelklick, Android-Dateizuordnung, tatsächliche WhatsApp-Übertragung und Öffnung in Connys privaten Apps sind weiterhin manuelle Gerätetests. Die statischen Exportdateien wurden wie oben beschrieben über erlaubtes lokales HTTP geprüft.
- Studio-/Review-/Presse-Links sind korrekt aus den gelieferten Quellen übernommen. Keine Änderung an Google-Profilen oder Rezensionen; keine behauptete Zustellung und kein Live-Hosting-Test.
- Vollständige Rechtstexte, finale Inhalts-/Bildfreigaben, Hauseingang/Klingel und genaue Parkplatzzufahrt/Stellplatznummer bleiben offen. Es wird keine unbekannte Information durch einen erfundenen Platzhalter ersetzt.
