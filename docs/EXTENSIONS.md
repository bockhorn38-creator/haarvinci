# Kundenakten und kundenbezogene Extensions ab Android 0.4.0

Das Haarprofil erweitert die bestehende Kundenakte um frei eingebbare Naturhaarfarbe, aktuelle Haarfarbe, Struktur, Dichte, aktuelle Extensions und Wünsche sowie optionale Längen in Zentimetern. Persönliche Notizen und bisherige Kontakte bleiben erhalten. Der aktuell getragene Look ist bewusst unabhängig von einer Bestellung: eine zugeordnete Position bedeutet noch keine Einarbeitung.

`extensions.ExtensionPosition` ist ein getrenntes Fachmodell mit UUID und obligatorischer Kundenverknüpfung. Es gibt keinen Lagerbestand und keine Warenbewegung. Hersteller, Art, Farbe und Hersteller-Farbcode sind Freitext. Vorhandene eigene Angaben werden als unverbindliche Eingabevorschläge angeboten. Jede Hersteller-/Farb-/Längenkombination wird als eigene Position erfasst.

Preise sind exakte Dezimalwerte mit zwei Nachkommastellen und gelten jeweils für die gesamte Position. Gewicht gilt ebenfalls für die gesamte Position; zusätzliche Anzahl und Einheit werden nur gemeinsam angegeben. Die Übersicht zeigt den Einkaufswert der aktuell gefilterten Positionen, keine offenen Rechnungsbeträge. Lieferstatus bezeichnet ausschließlich die Position, keinen Zahlungs- oder Besuchsstatus.

Anlage, Änderung und Löschung laufen atomar über Dienste und werden in `customers.CustomerEvent` dokumentiert. Das Ereignis behält eine Momentaufnahme und bei Änderungen Vorher-/Nachherwerte. Die UUID-Referenz ist absichtlich kein Fremdschlüssel auf die Position: auch nach deren bestätigter Löschung bleiben die ursprünglichen Angaben nachvollziehbar. Die Historie ist über die Oberfläche ausschließlich lesbar. Dies ist ein fachliches Änderungsprotokoll, keine manipulationssichere externe Revision.

Kundenbezogene Sperren und Versionsnummern verhindern stilles Überschreiben aus alten Formularen. Alle Abfragen einschließlich Suchvorschlägen, Historie und Export sind auf die angemeldete Eigentümerin begrenzt. Die Kundenzuordnung einer vorhandenen Position lässt sich nicht über Formulardaten verschieben. Löschung erfordert Bestätigung mit POST und CSRF-Schutz.

Die Historie sortiert nach Fachdatum, danach Erfassungszeit. Neue Zuordnungen erscheinen am Bestell-/Zuordnungsdatum; spätere Änderungen und Löschungen am tatsächlichen Bearbeitungstag. Bestehende Akten erhalten keine erfundenen früheren Ereignisse. Das erste Beratungsdatum bleibt separat sichtbar. Aus Positionen werden keine Besuchszahlen oder letzten Besuche abgeleitet.

Spätere Bestellpositionen und Behandlungen können auf die stabilen Kunden- und Positions-UUIDs verweisen. Anzahlungen, Teilzahlungen und Restbeträge gehören in ein separates Zahlungsmodell mit exakten Beträgen; sie werden hier nicht aus Lieferstatus oder Verkaufspreis abgeleitet. Die bestehenden Sicherungen erfassen auch die neuen Tabellen; eine zusätzliche Sicherungsfunktion wurde nicht entwickelt.

Die Migrationen ergänzen vorhandene Kundendaten um leere optionale Felder und neue Tabellen. Android und Windows verwenden denselben Fachkern. Androids generierte Quellen und das PyInstaller-Programmpaket enthalten auch das neue Modul `extensions` und seine Migrationen.
