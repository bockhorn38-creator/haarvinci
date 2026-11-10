# Behandlungen, Preise und Zahlungen – 0.6.0

Der gemeinsame Fachkern `treatments` arbeitet lokal auf Android/Windows mit SQLite und auf dem Server mit PostgreSQL. Alle hier beschriebenen Buchungen sind manuell dokumentierte Vorgänge. Es werden keine Karten belastet, Überweisungen ausgelöst oder Erstattungen an Banken gesendet. Ausschließlich fiktive Testdaten verwenden.

## Einen vollständigen Vorgang ausprobieren

1. Unter **Kundinnen** eine erfundene Person mit Kontaktmöglichkeit und optionalem Haarprofil anlegen. Mehrere Extensions-Positionen in derselben Akte erfassen.
2. Über **Behandlungen → Preisliste** eigene Reihen-Gesamtpreise und Zusatzleistungen anlegen. Die Preisliste ist anfangs bewusst leer: Connys tatsächliche Tarife wurden nicht vorgegeben. Für einen fiktiven Test beispielsweise zwei Reihen mit 145,00 € und eine Haarwäsche mit 20,00 € eintragen. Ein Reihenpreis ist der Gesamtpreis für diese Reihenanzahl, kein Preis, der noch einmal mit der Reihenanzahl multipliziert wird.
3. In der Kundenakte einen Termin vereinbaren. Im Termin **Behandlung erfassen** wählen. Kundin, Datum und vorhandene Extensions werden vorgegeben; die konkrete Auswahl prüfen. Ein Termin gehört höchstens zu einer Behandlung.
4. Zwei Reihen und die fiktive Haarwäsche wählen: **Preis prüfen** zeigt 165,00 €. Erst **Behandlung speichern** legt den Vorgang an. Alternativ einen individuellen Gesamtpreis vereinbaren. Dieser enthält bereits alle Leistungen und wird nicht zusätzlich zum berechneten Preis addiert.
5. Die Verkaufspreise der zugeordneten Extensions werden nur mit der ausdrücklichen Option zusätzlich berechnet. Einkaufspreise fließen nicht in den Behandlungspreis ein. Mengen verändern die gespeicherten Positions-Gesamtpreise nicht. Eine reine Verknüpfung berechnet die Extensions nicht erneut.
6. Im geplanten Vorgang **Zahlung dokumentieren**: fiktive Anzahlung 50,00 €, tatsächliches Zahlungsdatum und Zahlungsweg wählen. Der offene Rest beträgt 115,00 €.
7. Nach dem Termin die Behandlung bearbeiten, Dokumentation ergänzen und auf **Durchgeführt** setzen. Beim Bearbeiten bleibt die bisherige Preisvereinbarung voreingestellt. Ein zukünftiger Vorgang kann noch nicht durchgeführt sein. Der verknüpfte beendete Termin wird mit abgeschlossen; die Kundenstatistik zählt einen Besuch.
8. Eine Teilzahlung von 65,00 € und abschließend die Restzahlung von 50,00 € dokumentieren. Der Restbetrag ist 0,00 €. **Restzahlung** verlangt den vollständigen aktuellen Rest; kleinere Beträge gehören unter Teilzahlung.
9. Kundenakte, Historie und **Statistik** öffnen. App beenden und neu öffnen: Behandlung, Preisstand und Zahlungen bleiben erhalten. Eine bestehende `.haarvinci`-Sicherung enthält diese Daten ebenfalls.

Behandlungen sind auf Startseite, Konto und Kundenakte erreichbar; die vorhandene untere Navigation bleibt erhalten. Die App verlangt weder eine doppelte Kundenerfassung noch einen neuen Termin, wenn bereits passende Datensätze vorhanden sind.

## Preisvereinbarungen und Änderungen

Reihenanzahl: 1–20. Preise sind exakte EUR-Dezimalbeträge mit zwei Nachkommastellen, maximal 9.999.999,99 €. Eine fehlende aktive Preisstaffel wird erklärt; die App erfindet keinen Preis. Zusatzleistungen werden aus der eigenen Preisliste gewählt.

Gespeicherte Preiszeilen und Extensions-Momentaufnahmen gehören zum konkreten Behandlungsvorgang. Spätere Preislistenänderungen berechnen alte Behandlungen nicht neu. Beim Bearbeiten kann die bisherige Vereinbarung erhalten oder ausdrücklich neu berechnet werden. Ändern sich preisrelevante Angaben, muss der Preis erneut geprüft werden. Bei Änderungen zwischen Vorschau und Speicherung wird die Übernahme abgewiesen. Ein individueller Gesamtpreis erzeugt gegebenenfalls eine sichtbare Anpassungszeile.

Bereits eingegangene Beträge begrenzen eine nachträgliche Preisreduktion: gegebenenfalls zuerst eine tatsächliche Rückerstattung dokumentieren. Gelöschte Extensions-Positionen hinterlassen ihre Momentaufnahme im Behandlungsvorgang und in der Historie.

## Stornierungen, Rückerstattungen und Fehlerkorrektur

- **Behandlung stornieren** verlangt einen Grund. Die Forderung entfällt, vorhandene Nettozahlungen erscheinen als **Noch zu erstatten**. Es wird kein Geld automatisch zurückgegeben.
- **Rückerstattung dokumentieren** bezeichnet eine tatsächliche Rückgabe. Den ursprünglichen Zahlungseingang auswählen, Betrag und Grund angeben. Nie mehr als den noch nicht erstatteten Anteil dieses Eingangs zurückgeben. Bei mehreren Eingängen die Rückgaben getrennt zuordnen. Für einen aktiven Vorgang erhöht eine Rückerstattung den offenen Rest wieder.
- **Fehlerhafte Buchung stornieren** korrigiert eine versehentlich erfasste Buchung. Der ursprüngliche Eintrag bleibt mit Stornogrund sichtbar, wird aber nicht mehr gerechnet. Das ist keine tatsächliche Geldrückgabe. Ein Eingang mit aktiven Rückerstattungen kann erst nach Korrektur dieser Erstattungen storniert werden.
- Eine Terminabsage storniert eine verknüpfte, noch geplante Behandlung mit. Eine bereits durchgeführte Behandlung bleibt dokumentiert. Die Behandlung selbst zu stornieren sagt einen Kalendertermin nicht automatisch ab; einen weiterhin geplanten Termin gegebenenfalls gesondert absagen.
- Überzahlungen, negative/zu große Beträge, zukünftige Zahlungsdaten und Erstattungen über den ursprünglichen Eingang hinaus sind gesperrt. Zahlungen gehören immer zu einer konkreten Behandlung und deren Kundin.

Zahlungswege: bar, Überweisung, Karte, sonstiger Weg. Gleiche Buchungskennung verhindert doppelte Speicherung bei erneutem Absenden. Änderungen verwenden Besitz-, Versions- und Transaktionsprüfungen; fremde Kunden oder Vorgänge sind nicht auswählbar. Die Oberfläche bietet kein endgültiges Löschen von Behandlungen oder Zahlungen an.

## Was die Statistik bedeutet

| Anzeige | Berechnung |
| --- | --- |
| Leistungswert | Vereinbarte Preise durchgeführter Behandlungen nach Behandlungsdatum; stornierte Vorgänge ausgenommen |
| Zahlungseingänge | Tatsächlich dokumentierte, nicht stornierte Eingänge nach Zahlungsdatum |
| Davon Anzahlungen | Teilmenge dieser Eingänge mit Buchungsart Anzahlung |
| Rückerstattungen | Tatsächlich dokumentierte, nicht stornierte Rückgaben nach Zahlungsdatum |
| Netto-Geldzufluss | Eingänge abzüglich Rückerstattungen; kein Gewinn und keine Steuerberechnung |
| Durchschnitt je Behandlung | Leistungswert geteilt durch durchgeführte Behandlungen, auf Cent gerundet |
| Dokumentierte Besuche | Durchgeführte Behandlungen plus alte abgeschlossene Termine ohne Behandlung; verknüpfte Vorgänge zählen einmal |
| Offene Forderungen | Gesamtpreis abzüglich Eingänge zuzüglich Erstattungen bei geplanten/durchgeführten Behandlungen; immer alle Zeit |
| Erstattungsbedarf | Verbleibende Nettozahlungen stornierter Behandlungen; immer alle Zeit |

Der Zeitraumfilter bezieht sich je nach Kennzahl auf Leistungs- oder Zahlungsdatum. Forderungen und Erstattungsbedarf bleiben zeitunabhängig, damit ältere offene Beträge sichtbar bleiben. Die Geldbuchungsliste zeigt höchstens die letzten 100 Einträge; Summen berücksichtigen alle passenden Einträge. Kundenstatistiken verwenden dieselben Berechnungen mit Kundenfilter. Mehrere Extensions oder Preiszeilen vervielfachen die Geldsummen nicht.

## Import, Sicherung und Grenzen

`haarvinci.import` Version 2 kann zusammengehörige Kunden, Extensions, Termine, Behandlungen und Zahlungen in einem bestätigten Paket speichern. Version 1 bleibt unterstützt. Bestehende Akten und Behandlungsvorgänge immer eindeutig manuell auswählen. Fachregeln und Eigentümerprüfung gelten auch beim Import; bei Fehlern wird kein Teilpaket gespeichert. [Format und Beispiele](CHATGPT-IMPORT.md).

Die bestehende Sicherung und Benutzertrennung bleiben erhalten. Keine zusätzlichen Cloud-Dienste, Lagerverwaltung, automatische Banken-/Kassenanbindung, Rechnungsstellung, Steuer- oder Gewinnermittlung. Android-Gerätekalender und ChatGPT-Textübernahme bleiben die bestehenden nativen Wege. [Testnachweise und offene Geräteprüfungen](PRUEFUNG.md).
