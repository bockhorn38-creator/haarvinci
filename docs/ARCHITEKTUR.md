# Haarvinci – Architektur und erste Etappe

## Entscheidung vor der Implementierung

Ein modularer Monolith mit Django 5.2 LTS, Python 3.12 und PostgreSQL 17. Django bringt ausgereifte Anmeldung, Formularprüfung, Datenbankmigrationen, CSRF-Schutz und serverseitige Vorlagen mit. Das reduziert die Zahl der Abhängigkeiten und vermeidet zwei getrennte Anwendungen für Frontend und Backend. Die Oberfläche nutzt semantisches HTML, eigenes responsives CSS und sehr wenig JavaScript. Es gibt keine externe Schrift-, Tracking- oder Bildanbindung. Die Daten liegen ausschließlich in PostgreSQL, niemals im LocalStorage.

PostgreSQL läuft lokal in Docker; im späteren Betrieb empfiehlt sich ein verwalteter PostgreSQL-Dienst mit automatischen externen Sicherungen. Gunicorn und WhiteNoise sind für den Serverbetrieb vorgesehen. Alle konkreten Paketstände sind in uv.lock eingefroren. Django 5.2 ist eine langfristig unterstützte Version.

## Daten und Grenzen

`customers.Customer`: UUID, Eigentümerin, Vor-/Nachname, Telefonnummer und normalisierte Suchnummer, E-Mail, optionale Anschrift und Geburtstag, erste Beratung, Notizen, Erstellungs-/Änderungszeit und Bearbeitungsversion. Eine Kontaktmöglichkeit ist Pflicht. Namen sind bewusst nicht eindeutig: Zwei Kundinnen dürfen gleich heißen. Telefon/E-Mail sind ebenfalls keine verlässlichen Identitäten. Datenbankindex auf Eigentümerin und Namen; Suchbegriffe werden verknüpft, Telefonnummern auch ohne Formatierung gefunden.

`auth.User`: Django-Anmeldung mit Passwort-Hash, ohne öffentliche Registrierung. Jede Abfrage, Änderung und jeder Export wird auf die angemeldete Eigentümerin begrenzt. Die Eigentümerin wird ausschließlich serverseitig vergeben. Gleichzeitige Änderungen werden innerhalb einer Transaktion mit Zeilensperre und Versionsvergleich geschützt. Django-Sessions und der Anmeldeschutz von django-axes werden ebenfalls in PostgreSQL gespeichert.

`core`: Dashboard, Konto, Sicherheitsheader, App-Manifest und rein netzbasierter Service Worker. `customers`: Modelle, Eingabeprüfung, Dienste, Ansichten und Tests. Geschäftsänderungen gehören in Dienste, nicht in Templates. URLs verwenden UUIDs; Berechtigungsprüfungen sind trotzdem zwingend.

## Erste Etappe und Oberflächen

1. Anmeldung und Passwortänderung; Schutz vor wiederholten Fehlversuchen.
2. Start mit echten Kennzahlen aus der Datenbank und zuletzt angelegten Kundinnen.
3. Kundenbuch mit Suche, Seitennavigation und verständlichen Leerzuständen.
4. Kundenakte mit Kontakt, Beratungsdatum, Notizen und JSON-Export.
5. Erstellen/Bearbeiten mit serverseitiger Prüfung und Schutz vor Überschreiben.
6. Backups im PostgreSQL-eigenen Format, Integritätsprüfung und echte Wiederherstellungsprobe.
7. Tests mit PostgreSQL und Browserprüfung in Pixel-Größe.

Die Oberfläche ist deutsch, für Touch ausgelegt, mit unterer Navigation auf Smartphones. PWA-Manifest und Symbole ermöglichen Installation über HTTPS auf Android. Die Anwendung benötigt Internet. Personenbezogene Seiten werden weder im Service Worker noch im Browser-Cache gespeichert.

## Spätere Erweiterungen – noch nicht implementiert

- `calendar`: offizielle Google-OAuth-Anbindung, serverseitig verschlüsselte Refresh-Tokens, manuelle Zuordnung, eindeutige externe Ereignis-IDs, Wiederholungs-/Konfliktbehandlung. Privattermine nicht anhand von Titel vermuten.
- `extensions`: Hersteller → herstellerspezifischer Farbcode → Produkt; Methoden als Datensätze. Behandlungen erhalten mehrere Materialpositionen und dokumentierte Mischungen.
- `treatments`, `orders`: eigene Modelle mit geschützten Verweisen auf Customer. Bestellungen kundenbezogen statt umfassender Lagerverwaltung.
- `payments`: exakte Dezimalbeträge und getrennte Zahlungs-/Forderungszustände. Nur eingegangene Zahlungen zählen als Zahlungseingang.
- `reporting`: lesende Abfragen über gespeicherte Daten, eindeutige Definition von Umsatz, Zahlung und Materialkosten.
- `assistant`: Adapter an vorhandene Dienste. Änderungen zuerst als Vorschlag und erst nach Bestätigung ausführen. Keine KI-Abhängigkeit in Phase 1.

Es werden keine leeren Datenbanktabellen, Fake-Kalender oder funktionslosen Menüpunkte vorab gebaut. Kein Löschen von Kundinnen in Phase 1; Lösch-/Aufbewahrungsregeln werden vor echtem Betrieb fachlich festgelegt. Export ist bereits verfügbar.
