# Kalender und Termine ab Android 0.5.0

Haarvinci speichert Termine lokal in SQLite; die Servervariante verwendet dieselben Modelle auf PostgreSQL. Der lokale Kalender benötigt kein Google-Konto und kein Internet. Bestehende Kundendaten, Haarprofile, Extensions, Anmeldung und Gestaltung bleiben erhalten.

## Bedienung

Unten **Kalender** öffnen. **Tag**, **Woche** und **Monat** wechseln die Ansicht, Pfeile den Zeitraum, **Heute** führt zum aktuellen Datum zurück. Das Datumsfeld erlaubt einen direkten Sprung. Einen Kundentermin antippen, um Details und die Kundenakte zu öffnen. In der Monatsansicht öffnet die Tageszahl den Tag, ein sichtbarer Termin direkt seine Details.

**Neuer Termin** öffnet das Formular mit Kundin, Terminart, Datum, Beginn/Ende, optionalem Puffer danach, Status und Notizen. Die tatsächliche Dauer wird automatisch berechnet. Für mehrtägige Zeitgrenzen bis maximal 24 Stunden lässt sich ein abweichendes Enddatum aufklappen. Die regulären freien Zeiten werden von 08:00 bis 20:00 angezeigt, Termine außerhalb dieses Fensters erweitern die Tagesdarstellung. Das ist ein Anzeigefenster, keine erfundene Öffnungszeit und keine Buchungssperre.

**Bearbeiten / verschieben** verändert einen bestehenden Termin. Eine Überschneidung einschließlich der Puffer löst eine Warnung aus; ohne eine ausdrückliche Bestätigung wird nicht gespeichert. **Termin absagen** verlangt eine Bestätigung und erhält den Termin als abgesagt. Veraltete Formulare dürfen neuere Änderungen nicht überschreiben.

Die Kundenakte zeigt den nächsten/laufenden Termin, den letzten abgeschlossenen Besuch, vergangene und abgesagte Termine. Nur Termine mit Status **Abgeschlossen** und tatsächlichem Ende in der Vergangenheit zählen als Besuche. Eine vergangene Planung wird nicht automatisch zum abgeschlossenen Besuch; Absagen zählen nie. Termine sind noch keine Behandlungen, Rechnungen oder Zahlungen.

## Technische Grenzen und Erweiterungen

- `appointments.Appointment` gehört ausdrücklich zu einer Eigentümerin, Kundin und Terminart. `AppointmentType` enthält sieben vorgegebene Arten und erlaubt eigene, nur für die Eigentümerin sichtbare Ergänzungen.
- Datum/Uhrzeiten werden als echte zeitzonenbehaftete Zeitpunkte gespeichert. Die Eingabe gilt für Europe/Berlin; Dauer wird über UTC berechnet. Nicht existente oder mehrdeutige Uhrzeiten an Zeitumstellungen werden erklärt und abgewiesen.
- Dienste sperren die Eigentümerin während lokaler Kalenderänderungen; SQLite verwendet IMMEDIATE-Transaktionen. Versionsnummern sichern Bearbeiten und Absagen ab. Änderungen werden atomar in der Kundenhistorie dokumentiert.
- Google-Verknüpfungen, fremde geschäftliche Belegungen und private Belegt-Zeiten sind eigene Modelle. `PrivateBusy` hat ausschließlich Verknüpfung und Zeitgrenzen, keine Felder für Titel, Beschreibung oder Teilnehmer.
- Eigene Google-Ereignisse haben feste IDs, Installations-/Terminzuordnung und ETags. Offline-Änderungen bleiben in der lokalen Datenbank ausstehend. Nach einem unklaren Insert-Ausgang wird dieselbe ID abgeglichen; abweichende Stände ohne sichere Vergleichsbasis werden zum Konflikt.
- Synchronisierung liest zunächst einen vollständigen, paginierten Belegungsausschnitt (90 Tage zurück, 365 Tage voraus) und ersetzt den Cache erst nach vollständiger Antwort. Fremde Google-Wiederholungen und ganztägige Ereignisse werden als Belegung berücksichtigt. Kein Google-Webhook oder dauerhaft laufender Synchronisierungsserver erforderlich.
- Synchronisierungskonflikte erhalten beide Stände. Die Android-App bietet nach Bestätigung die Übernahme des Google-Stands oder die Verwendung des lokalen Stands; eine erneute Änderung seit der Anzeige führt erneut zur Prüfung. Ein bewusst lokal beibehaltener, bei Google bereits gelöschter Termin erhält eine neue Ereignisgeneration.
- Google-Belegungen außerhalb des zuletzt abgefragten Fensters oder seit einem ausgefallenen Abgleich sind offline nicht bekannt. Der letzte erfolgreiche Zeitpunkt und das Fenster stehen bei den Verbindungen. Eine Konfliktfreiheit gegenüber unbekannten Google-Änderungen wird nicht behauptet.

Google-Einrichtung, getrennte Konten, native Tokenablage und tatsächliche Grenzen der Konto-Prüfung: [GOOGLE-KALENDER.md](GOOGLE-KALENDER.md).
