# ChatGPT-Import auf Android (Testversion 0.5.1)

Es werden keine OpenAI-API, Kontoverknüpfung und externen Server verwendet. ChatGPT erzeugt Text, Haarvinci validiert ihn lokal. Kundenakten, Haarprofile, kundenbezogene Extensions und Termine können in einem Paket übernommen werden. Keine Lagerbuchungen.

## Auf dem Pixel ausprobieren

1. Mit fiktiven Daten arbeiten. In ChatGPT den untenstehenden Prompt und die Vorlage verwenden und die gewünschten Angaben diktieren.
2. Den **vollständigen Antworttext** kopieren. In Haarvinci anmelden und im Programmmenü **Aus ChatGPT einfügen** antippen; alternativ unter **Konto → Aus ChatGPT übernehmen**. Die Zwischenablage wird ausschließlich bei dieser Aktion gelesen. Haarvinci ruft keine Links ab und liest keine geteilten Dateien.
3. Alternativ den Antworttext über Android **Teilen → Haarvinci** übergeben. Haarvinci ist als nativer Empfänger für `ACTION_SEND` und `text/plain` registriert. Vor einer Anmeldung wird der Text nur im Prozessspeicher gehalten. Nach der Anmeldung erscheint die Vorschau.
4. Fehlende Pflichtfelder ergänzen und Zuordnungen prüfen. Für bestehende Kundinnen stets eine konkrete Akte auswählen (Name, Kontakt, Aktenkennung). Kein automatisches Zuordnen anhand eines Namens. Bei Änderungen einer vorhandenen Akte die Änderungsfreigabe markieren.
5. **Angaben prüfen**, dann die abschließende Übersicht kontrollieren und **Jetzt verbindlich übernehmen** drücken. Erst diese ausdrückliche Bestätigung speichert das gesamte Paket in einer Transaktion. Abbrechen oder App schließen speichert keine importierten Fachdaten.

Vorschauen verfallen nach 30 Minuten, bleiben ausschließlich im RAM und sind an die konkrete Anmeldung gebunden. Maximal drei Pakete pro Nutzerin werden gehalten. Nach erfolgreicher Bestätigung wird der personenbezogene Entwurf gelöscht. Die Datenbank speichert eine Importquittung mit Kennung, Prüfsummen und Anzahlen; kein zusätzliches Rohtextarchiv. Die Quittung verhindert wiederholtes Anlegen desselben Pakets. Die bestehenden lokalen Sicherungen enthalten die bestätigten Einträge und Quittungen.

### ChatGPT-Teilen unter Android

Die Android-Schnittstelle akzeptiert echten Text, auch aus anderen Apps. Die ChatGPT-Funktion zum Teilen einer **Unterhaltung** kann dagegen einen `https://chatgpt.com/share/…`-Link erzeugen. Ein solcher Link ist kein Datenpaket; Haarvinci erklärt dann den Kopierweg. Laut OpenAI beschreibt die [Shared Links FAQ](https://help.openai.com/en/articles/7925741-chatgpt-shared-links-faq) diese Freigabe ausdrücklich als URL. Welche Aktion die installierte ChatGPT-Version für eine einzelne Antwort anbietet, kann sich ändern. Verlässlicher Fallback: Antwort **kopieren**, dann in Haarvinci bewusst einfügen.

Automatisiert wird ein Android-Sende-Intent mit vollständigem Text sowie ein reiner Teilen-Link geprüft, außerdem das tatsächliche Android-Clipboard beim Tippen des Menüs. Das ist kein Test einer angemeldeten echten ChatGPT-App. Auf deinem Pixel bitte zusätzlich prüfen, ob die aktuelle ChatGPT-Antwortaktion echten Text übergibt. Kein Download aus ChatGPT oder Anmeldung bei ChatGPT ist für Haarvinci nötig.

## Prompt zum Kopieren

> Erstelle aus meinen Angaben genau ein Haarvinci-Importpaket im folgenden JSON-Format `haarvinci.import`, Version 1. Gib nur einen JSON-Codeblock aus. Erzeuge eine neue UUID als `id`. Erfinde keine fehlenden Fakten, Kontaktdaten, Preise oder Termine. Fehlende Angaben leer lassen; ich ergänze sie in der Vorschau. Für jede Kundin eine eindeutige kurze `ref` vergeben. Bei einer neuen Kundin `mode: "new"`; für eine bereits vorhandene Kundin `mode: "existing"`, einen `hint` zur manuellen Suche angeben und in `data` ausschließlich ausdrücklich gewünschte Änderungen aufnehmen. Kundinnen werden in Haarvinci manuell ausgewählt; niemals Datenbank-IDs erfinden. Extensions und Termine über `customer_ref` zuordnen. Ausschließlich die unten dokumentierten Felder und Werte verwenden. Daten YYYY-MM-DD, Uhrzeiten HH:MM in Europe/Berlin. Bei unklaren Datumsangaben nachfragen. Preise sind Gesamtpreise der Position. Beispiel- oder Platzhalterwerte niemals als meine Angaben übernehmen.

Vorlage mit **ausschließlich fiktiven** Daten (nicht unverändert wiederverwenden; immer neue `id`):

```json
{
  "format": "haarvinci.import",
  "version": 1,
  "id": "cec9532b-eaa5-43ae-abaa-3ebebbc4872c",
  "customers": [
    {
      "ref": "k1",
      "mode": "new",
      "data": {
        "first_name": "Lina",
        "last_name": "Fiktivblüte",
        "email": "lina@example.com",
        "phone": "+49 151 0000 0101",
        "natural_color": "Dunkelblond",
        "hair_structure": "Wellig",
        "desired_length": "50,5",
        "hair_wishes": "Mehr natürliche Fülle"
      }
    }
  ],
  "extensions": [
    {
      "customer_ref": "k1",
      "data": {
        "manufacturer": "Fiktivhaar Atelier",
        "extension_type": "Tape-Ins",
        "color": "Blond",
        "length_cm": "50,5",
        "weight_g": "100,25",
        "purchase_price": "149,90",
        "sale_price": "249,95",
        "assigned_on": "2026-11-20",
        "delivery_status": "planned"
      }
    }
  ],
  "appointments": [
    {
      "customer_ref": "k1",
      "data": {
        "appointment_type": "Erstberatung",
        "day": "2026-11-20",
        "begin": "10:00",
        "finish": "11:00",
        "buffer_minutes": "15",
        "status": "planned",
        "notes": "Fiktives Beratungsgespräch"
      }
    }
  ]
}
```

Für bestehende Kundinnen ohne Änderung am Profil:

```json
{"ref":"k1","mode":"existing","hint":"Lina Fiktivblüte, Kontakt endet 0101","data":{}}
```

Diesen Kundinnenblock im vollständigen Paket verwenden. Haarvinci verlangt dann die konkrete Aktenauswahl. Eine neue Kundin kann in der Vorschau ebenfalls einer vorhandenen Akte zugeordnet werden; dabei werden die vorgeschlagenen persönlichen Angaben nicht stillschweigend übernommen.

## Feldreferenz Version 1

- Paket: `format`, `version`, `id`, `customers` erforderlich; `extensions` und `appointments` optional (leere Listen). 1–10 Kundenreferenzen, jeweils maximal 25 Extensions/Termine; Text maximal 64 KiB UTF-8. Keine unbekannten Felder, doppelten JSON-Schlüssel, verschachtelten Datenwerte, NaN/Infinity oder automatischen Aktionen.
- Kundin: `ref` (1–40 Buchstaben/Zahlen/Unterstrich/Bindestrich, eindeutig), `mode` (`new`, `existing`), optional `hint` (maximal 200 Zeichen), `data`.
- Persönliche Daten: `first_name`, `last_name`, `phone`, `email`, `street`, `postal_code`, `city`, `birthday`, `first_consultation`, `notes`. Bei Neuanlage Vorname, Nachname sowie Telefon oder E-Mail nötig. Keine echten Daten zum Testen.
- Haarprofil: `natural_color`, `current_color`, `hair_structure`, `natural_length`, `desired_length`, `hair_density`, `current_extensions`, `hair_wishes`. Längen in cm; Werte unterliegen derselben Prüfung wie im Kundenformular.
- Extensions: `customer_ref`, `data` mit `manufacturer`, `extension_type`, `color`, optional `color_code`, `length_cm`, `weight_g`, `quantity`, `quantity_unit`, `purchase_price`, `sale_price`, `assigned_on`, `delivery_status`, `notes`. Hersteller/Art/Farbe/Länge/Gewicht/Einkaufspreis/Zuordnungsdatum erforderlich. Länge 0,1–300 cm, Gewicht 0,01–10000 g, Preise nicht negativ. Dezimalwerte ohne Tausendertrennzeichen als Text mit Komma oder Punkt. Anzahl und Einheit gemeinsam oder beide leer; Einheiten `strands`, `packs`, `pieces`. Lieferstatus leer oder `planned`, `ordered`, `received`, `cancelled`.
- Termin: `customer_ref`, `data` mit `appointment_type` (genauer vorhandener deutscher Name, z. B. `Erstberatung`; unbekannte/mehrdeutige Namen in der Vorschau auswählen), `day`, `begin`, `finish`, optional `end_day`, `buffer_minutes` (0–240), `status` (`planned`, `confirmed`, `completed`, `cancelled`), `notes`. Voreinstellung geplant/kein Puffer. Ende nach Beginn, maximal 24 Stunden; zukünftige Termine nicht abgeschlossen. Mehrdeutige/nicht existierende Uhrzeiten bei Zeitumstellung werden erklärt und abgewiesen.

Identische Extensions und identische Kunden-/Zeitkombinationen bei Terminen sowie Wiederholungen innerhalb des Pakets werden abgefangen. Ähnliche Kundinnen verlangen ausdrückliche Zuordnung oder eine bewusste andere Neuanlage. Zeitüberschneidungen werden nicht automatisch freigegeben: zuerst Zeiten korrigieren oder später im normalen Terminformular bewusst entscheiden. Erneute Versions-, Dubletten- und Terminprüfung direkt vor der atomaren Speicherung; bei zwischenzeitlichen Änderungen wird nichts teilweise übernommen. Importpakete sind Daten, keine Anweisungen zur Ausführung von Code oder Netzwerkaufrufen.
