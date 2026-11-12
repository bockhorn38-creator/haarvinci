# HaarVinci Signature 1.1.1 – Prüfstand

Stand: **12. November 2026**. Bestehende Astro-Website gezielt erweitert. Kein Livegang und keine Änderungen an Android-/Windows-/Django-App, IONOS, Domain, DNS oder E-Mail.

**Foto-Freigabe erteilt, Dateien fehlen:** Timo Bockhorn hat die acht Vorher-Nachher-Fotos ausdrücklich freigegeben. Die aktuelle Anweisung ersetzt die alten Sperrvermerke und ist in `content/media-approval.json` dokumentiert. Die acht Galerie-JPGs liegen weiterhin nicht als importierbare Dateien vor und sind im tatsächlich zugänglichen älteren ZIP nicht enthalten. Deshalb wird keine Originalbildintegration oder visuelle Abnahme der vier neuen Paare behauptet. Der Import- und Galeriepfad ist mit ausdrücklich fiktiven Testflächen funktional geprüft.

## Erfolgreiche technische Prüfungen

- Astro-/TypeScript-Check für 30 Dateien ohne Fehler, Warnungen oder Hinweise. Generierte Playwright-Berichte sind aus der Quellprüfung ausgeschlossen. Prettier und Git-Diff-Prüfung erfolgreich.
- **53 Chromium-/Playwright-Prüfungen:** bestehende Prüfungen einschließlich Signature-Galerie, dazu die prominenten Social-Buttons und gekennzeichneten Bewertungsauszüge. Der tatsächliche statische Build und die tatsächlichen HTML-Exportdateien werden geprüft, keine Ersatzoberfläche.
- Statischer Build mit Startseite, Impressums- und Datenschutzentwürfen sowie 404. Bestehende Preise, Haarmaterial-Vorauszahlung, fünf Bestellschritte, Weaving-Methode samt möglichen Mikroringen am Cornrow-Ende und Pflege-/Fremdhaarabgrenzungen erhalten.
- Instagram- und Google-Bewertungsbuttons im oberen Bereich bei 360, 390, 412, 768 und 1440 Pixeln, mindestens 48 Pixel hoch. Lokaler Bewertungsanker funktioniert. Drei korrekt gekennzeichnete Auszüge aus den gelieferten öffentlichen Google-Rezensionen, jeweils mit belegten individuellen fünf Sternen. Kein erfundener Gesamtdurchschnitt, Zähler oder AggregateRating-Markup. Google-Profil und Bewertungsabgabe korrekt getrennt; Presse verweist nur auf die gelieferte KN-URL. Keine fremden Screenshot-Bilder oder Heilversprechen.
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

Ein isoliertes temporäres Testprojekt verwendet acht geometrische JPEG-Testflächen mit fiktiven Metadaten, keine echten neuen Kundinnenfotos. Es prüft den Originalimport mit SHA-256-Kontrolle, lehnt manipulierte Dateien ab und lässt bereits geprüfte Privatkopien dabei unverändert. Die private Ausgabe landet ausschließlich unter `.private-preview/`. Ein normaler Build schließt die ungeklärten Testpaare aus. Anschließend wird im selben Testprojekt die ausdrückliche Freigabe simuliert: Der geprüfte Import aktiviert die Paarzuordnung, und alle vier Paare erscheinen im normalen Build. Abweichende CLI-Ausgabeziele für private Builds und ein Export privater Bilder in den normalen Downloadordner werden blockiert. Der eigentliche Katalog bleibt durch den Test unverändert.

Alle vier echten Paare haben `websiteApproved: true` gemäß der aktuellen Nutzeranweisung. `pairConfirmed: false` bleibt bis zur erfolgreichen Originaldateiprüfung bestehen; dies ist kein offener Zustimmungsbedarf. Alle fünf globalen Schalter in `content/release.json` bleiben `false`, da kein Livegang beauftragt ist. Private Bildvorschau und öffentlicher Release blockieren einander technisch. Der positive Release-Test läuft nur mit technischen Rechtstextmarkern in einem getrennten temporären Projekt; keine Marker gelangen in die gelieferten Vorschauen. `noindex` wird nicht als Datenschutz-Zugriffsschutz verwendet.

## Visuelle und lokale Ladebeobachtung

Vollständige Screenshots bei 390, 412 und 1440 Pixeln; ergänzende Ansichten von Ergebnissen, Vertrauen, Conny und Anfahrt. Kontrolliert wurden Lesbarkeit, Header, ganze Haarbilder, Kontraste, Inhalte und Kontaktaktionen.

Die Bildschirmansichten werden bei 390, 412 und 1440 Pixeln kontrolliert. Ein zuvor beobachteter Sprung der mobilen Kopfzeile bei langsamer JavaScript-Ausführung ist durch einen Regressionstest abgesichert. Lokale Messungen sind keine Lighthouse-Bewertung, kein mobiler Netzwerktest und keine zugesicherten Pixel-Leistungswerte.

## Reproduzieren

```bash
npm run check
npm run format:check
npm run build
npm run export:preview
npm test
```

Für die echte neue Galerie zusätzlich zuerst `npm run import:signature -- PFAD_ZUM_ENTPACKTEN_UEBERGABEORDNER`, danach `npm run build` und `npm run export:preview`. Der Import benötigt die fehlenden Original-JPGs; die bestehende ausdrückliche Freigabe wird übernommen, die Dateiprüfung aktiviert die vorgegebene Paarzuordnung.

## Grenzen und offene Abnahme

- Die acht Original-JPGs fehlen. Ein kleines ZIP mit diesen Dateien genügt. Foto-Freigabe liegt vor; die Zuordnung stammt aus dem Masterbriefing. Keine erneute Foto-Freigabe verlangen.
- Der Cloud-Browser sperrt direkte `file://`-Navigation. Windows-Doppelklick, Android-Dateizuordnung, tatsächliche WhatsApp-Übertragung und Öffnung in Connys privaten Apps sind weiterhin manuelle Gerätetests. Die statischen Exportdateien wurden wie oben beschrieben über erlaubtes lokales HTTP geprüft.
- Studio-/Review-/Presse-Links sind korrekt aus den gelieferten Quellen übernommen. Keine Änderung an Google-Profilen oder Rezensionen; keine behauptete Zustellung und kein Live-Hosting-Test.
- Vollständige Rechtstexte, finale Livegang-Freigabe, Hauseingang/Klingel und genaue Parkplatzzufahrt/Stellplatznummer bleiben offen. Es wird keine unbekannte Information erfunden.
