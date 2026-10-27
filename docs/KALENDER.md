# Kalender und Termine ab Android 0.5.0

Haarvinci speichert Termine lokal in SQLite; die Servervariante verwendet dieselben Modelle auf PostgreSQL. Der lokale Kalender benötigt kein Google-Konto und kein Internet. Bestehende Kundendaten, Haarprofile, Extensions, Anmeldung und Gestaltung bleiben erhalten.

## Bedienung

Unten **Kalender** öffnen. **Tag**, **Woche** und **Monat** wechseln die Ansicht, Pfeile den Zeitraum, **Heute** führt zum aktuellen Datum zurück. Das Datumsfeld erlaubt einen direkten Sprung. Einen Kundentermin antippen, um Details und die Kundenakte zu öffnen. In der Monatsansicht öffnet die Tageszahl den Tag, ein sichtbarer Termin direkt seine Details.

**Neuer Termin** öffnet das Formular mit Kundin, Terminart, Datum, Beginn/Ende, optionalem Puffer danach, Status und Notizen. Die tatsächliche Dauer wird automatisch berechnet. Für mehrtägige Zeitgrenzen bis maximal 24 Stunden lässt sich ein abweichendes Enddatum aufklappen. Die regulären freien Zeiten werden von 08:00 bis 20:00 angezeigt, Termine außerhalb dieses Fensters erweitern die Tagesdarstellung. Das ist ein Anzeigefenster, keine erfundene Öffnungszeit und keine Buchungssperre.

**Bearbeiten / verschieben** verändert einen bestehenden Termin. Eine Überschneidung einschließlich der Puffer löst eine Warnung aus; ohne eine ausdrückliche Bestätigung wird nicht gespeichert. **Termin absagen** verlangt eine Bestätigung und erhält den Termin als abgesagt. Veraltete Formulare dürfen neuere Änderungen nicht überschreiben.

Die Kundenakte zeigt den nächsten/laufenden Termin, den letzten abgeschlossenen Besuch, vergangene und abgesagte Termine. Nur Termine mit Status **Abgeschlossen** und tatsächlichem Ende in der Vergangenheit zählen als Besuche. Eine vergangene Planung wird nicht automatisch zum abgeschlossenen Besuch; Absagen zählen nie. Termine sind noch keine Behandlungen, Rechnungen oder Zahlungen.

## Technische Grenzen und Erweiterungen

Ab Android 0.5.1 verwendet die App direkt `CalendarContract`. Die aktiven Zuordnungen und Caches heißen `DeviceCalendarConnection`, `DeviceEventBinding`, `DeviceBusinessEvent` und `DevicePrivateBusy`. Eigene Ereignisse werden anhand zufälliger Marker und eines Vergleichsstands verwaltet; atomare Provider-Assertions verhindern unbemerktes Überschreiben. Private Daten enthalten ausschließlich Zeitgrenzen. Die Geschäftsregeln des lokalen Kalenders bleiben erhalten.

[Android-Gerätekalender einrichten, technische Grenzen und Pixel-Prüfliste](ANDROID-GERAETEKALENDER.md). Die alten REST-/OAuth-Modelle bleiben für die Migration bestehender Testinstallationen erhalten, werden aber durch den aktiven Android-Pfad nicht verwendet. Ein eigener OAuth-Anmeldeserver und ein Google-Cloud-Projekt sind für diese Testversion nicht erforderlich.
