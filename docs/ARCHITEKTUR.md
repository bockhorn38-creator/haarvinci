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
- Optionale spätere Produktvorlagen können häufig verwendete Hersteller-/Farbkombinationen aus dem bereits vorhandenen kundenbezogenen Modul `extensions` wiederverwenden. Eine Lagerverwaltung ist nicht vorgesehen.
- `treatments`, `orders`: eigene Modelle mit geschützten Verweisen auf Customer. Bestellungen kundenbezogen statt umfassender Lagerverwaltung.
- `payments`: exakte Dezimalbeträge und getrennte Zahlungs-/Forderungszustände. Nur eingegangene Zahlungen zählen als Zahlungseingang.
- `reporting`: lesende Abfragen über gespeicherte Daten, eindeutige Definition von Umsatz, Zahlung und Materialkosten.
- `assistant`: Adapter an vorhandene Dienste. Änderungen zuerst als Vorschlag und erst nach Bestätigung ausführen. Keine KI-Abhängigkeit in Phase 1.

Es werden keine leeren Datenbanktabellen, Fake-Kalender oder funktionslosen Menüpunkte vorab gebaut. Kein Löschen von Kundinnen in Phase 1; Lösch-/Aufbewahrungsregeln werden vor echtem Betrieb fachlich festgelegt. Export ist bereits verfügbar.

## Desktop-Version für Windows (0.2)

Der aktuelle Auftrag ergänzt eine eigenständige Windows-Anwendung. PySide6/Qt WebEngine zeigt dieselben fachlichen Oberflächen in einem eigenen, abgeschotteten Programmfenster. Waitress startet den Django-Kern intern an 127.0.0.1 mit zufälligem Port; ein pro Start erneuerter privater Header schränkt den Zugriff auf dieses Fenster ein. Es gibt keinen Node-Zugriff, keine JavaScript-Brücke zu Dateisystemfunktionen und keine freien externen Navigationen.

Getrennte Einstellungen nutzen gemeinsame Fachmodule: `config.settings` für PostgreSQL/Server, `config.desktop_settings` für SQLite/Desktop. SQLite ist hier die echte lokale Datenbank einer Einzelplatzanwendung; sie wird mit dem Programm geliefert und benötigt keinen separaten Datenbankdienst. Explizite IMMEDIATE-Transaktionen schützen Änderungen auch auf SQLite vor paralleler Überschreibung. Suchdaten werden in Unicode-NFKC/Casefold normalisiert, damit Umlaute und ß auf beiden Datenbanken konsistent gefunden werden. Bestehende Daten werden durch Migration ergänzt.

Der erste Start richtet einen persönlichen Zugang ein. Wahlweise werden sechs fiktive Testkundinnen angelegt. Fenster, Sicherungsdialoge, Export, Vergrößerung und Wiederherstellung gehören zur Desktop-Hülle. Sicherungen verwenden einen konsistenten SQLite-Snapshot in einer einzelnen geprüften `.haarvinci`-Datei. Sie enthalten keine Klartextpasswörter. Vor einer Wiederherstellung wird der aktuelle Datenstand zusätzlich gesichert; der eigentliche Austausch erfolgt vor Dienststart und unter Instanzsperre.

PyInstaller bündelt Python, Qt, Django, Waitress, Vorlagen und statische Dateien. Inno Setup erstellt einen deutschen Installer mit Desktop-/Startmenüverknüpfung. Benutzerdaten liegen außerhalb des Installationsordners und bleiben bei einer Deinstallation erhalten. Die Windows-Installation wird auf Windows gebaut und das tatsächlich installierte Programm mit fiktiven Daten geprüft. Der Desktop-Stand benötigt kein Internet; mehrere Geräte werden noch nicht synchronisiert.

## Android und nächste Etappe (0.4)

Die eigenständige Android-Hülle mit Chaquopy und System-WebView verwendet denselben Django-Kern und eine private SQLite-Datenbank. Android benötigt für die Kundenverwaltung keinen Server und keine Internetverbindung. Die oberen Abschnitte zum Hosting beschreiben ausschließlich die ursprüngliche Servervariante.

Kundenverwaltung und kundenbezogene Extensions sind erweitert: optionale strukturierte Haarprofile auf `Customer`, separate `extensions.ExtensionPosition` mit exakten Dezimal-Gesamtpreisen und `customers.CustomerEvent` für chronologische Momentaufnahmen/Vorher-/Nachherwerte. Details, Datumssemantik, Löschhistorie und spätere Verknüpfungen sind in [EXTENSIONS.md](EXTENSIONS.md) beschrieben. Hersteller und Farbcodes bleiben freie Eingaben. Es gibt keine Lagerbestände oder vorbereiteten Zahlungsattrappen.
