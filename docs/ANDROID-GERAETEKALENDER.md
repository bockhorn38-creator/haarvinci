# Android-Gerätekalender ab 0.5.1

Die Android-App verwendet jetzt direkt `CalendarContract` statt des zuvor vorbereiteten OAuth-Anmeldeservers. Es sind keine Domain, kein eigener Server und kein Google-Cloud-Projekt erforderlich. Google-Konten und Google-Kalender müssen bereits im Android-System eingerichtet und synchronisiert sein. Windows verwendet weiterhin seinen lokalen Kalender.

## Bedienung

Im Kalender **Gerätekalender** öffnen und zunächst einen **geschäftlichen**, beschreibbaren Kalender auswählen. Die native Android-Auswahl zeigt Kalendername und Konto. Haarvinci fragt die benötigten Android-Kalenderberechtigungen erst bei dieser Auswahl ab. Für privat reicht Lesen; geschäftlich werden Lesen und Schreiben benötigt. Ein zweiter, anderer privater Kalender darf aus einem anderen Google-Konto stammen.

Aktive Haarvinci-Termine werden dem Geschäftskalender zugeordnet. Andere dort vorhandene Termine werden schreibgeschützt als Belegung gezeigt. Private Termine erscheinen ausschließlich als **Privat belegt**. Für private Vorkommen fragt die App nur Beginn, Ende und Ganztagskennzeichen ab, keine Titel, Beschreibungen oder Teilnehmer; gespeichert werden nur Beginn/Ende. Androids Berechtigungsdialog gewährt technisch einen breiteren Zugriff. Die App beschränkt den tatsächlich genutzten Zugriff wie beschrieben. Zum Erkennen einer verschobenen eigenen Zuordnung wird ergänzend nur nach dem zufälligen App-Marker gesucht und ausschließlich Ereignis-ID/Kalender-ID gelesen, ohne private Inhalte.

Die Anmeldung in Haarvinci und der lokale Kalender bleiben unabhängig vom Google-Konto nutzbar. Bei fehlenden Berechtigungen bleiben lokale Änderungen erhalten; die Geräteverbindung erklärt den Fehler. Die Einstellungen verlinken auf die Android-Appberechtigungen und Kontosynchronisierung.

## Zuordnung, Offline-Verhalten und Konflikte

- Native Java-Schicht, Chaquopy-Aufrufe aus der vertrauenswürdigen App; **keine JavaScript-Schnittstelle** zur WebView. Native Aktionen erfordern eine echte Geste auf der lokalen Appseite, App-Zugriffscookie und angemeldete Sitzung.
- Zufälliger eindeutiger Marker je Terminverknüpfung, Provider-ID und Kalenderfingerabdruck (Konto/Typ/Name/Eigentümer). Keine Zuordnung anhand ähnlicher Titel. Eigene App-Metadaten plus kurzer `[Haarvinci-Verknüpfung: …]`-Hinweis in der **geschäftlichen Beschreibung** ermöglichen Wiedererkennung, auch wenn ein Synchronisationsdienst App-Metadaten entfernt. Diesen Hinweis nicht entfernen. Fremde und private Termine werden niemals geändert.
- Dauerhafte Schreibabsicht **vor** einer ersten Provider-Anlage; nach unklarem Ergebnis zunächst Zuordnung suchen, niemals blind eine Kopie anlegen. Wiederholter Abgleich ist idempotent. Provider-Schreiboperationen verwenden transaktionale `applyBatch`-Vergleiche des Kalenders und des vollständigen benötigten Ereignisstands mit erwarteten Zeilenanzahlen; ein inzwischen geänderter Stand wird nicht überschrieben.
- Vergleich mit gespeichertem letztem gemeinsamen Stand: ausschließlich lokale Änderungen werden übertragen, ausschließlich Geräteänderungen mit Historieneintrag übernommen. Bei beidseitigen Änderungen verlangt die Termindetailseite eine ausdrückliche Entscheidung. Auswahl enthält Versions-/Konfliktprüfung und erneutes Lesen des Providers. Fremde Änderungen zwischen Vorschau und Bestätigung werden erkannt.
- Bei verlorenen Markern, Mehrfachzuordnung, Kalenderwechsel oder Umwandlung in eine Wiederholungsreihe stoppt die automatische Änderung. Ein fehlendes Ereignis könnte gelöscht oder nach Konto-/Cache-Neuaufbau noch nicht synchronisiert sein. Deshalb keine automatische Ersatzanlage. Nutzerin kann bewusst die Absage übernehmen oder den lokalen Termin behalten und die Verknüpfung pausieren; ebenfalls erneut prüfen. Ein Wechsel des Geschäftskalenders mit bestehenden Verknüpfungen ist gesperrt.
- Lokale Absage entfernt ausschließlich das sicher zugeordnete eigene Geräteereignis. Eine bewusst lokal reaktivierte, zuvor bestätigte Absage erhält eine neue Verknüpfung.
- Offline werden lokale Änderungen dauerhaft gespeichert und auf den lokalen Calendar Provider angewandt. Android übernimmt später die Google-Kontosynchronisierung. Es werden keine Teilnehmer angelegt oder eingeladen.
- WorkManager und ContentObserver lösen Abgleiche aus; Android entscheidet über den tatsächlichen Hintergrundzeitpunkt. Manuelles **Gerätekalender abgleichen** ist zusätzlich vorhanden. Die App bestätigt einen **Geräteabgleich**, keine garantierte Google-Cloud-Übertragung. Ausgeschaltete Android-Synchronisierung wird separat angezeigt.
- Fremde wiederkehrende Ereignisse werden durch `Instances` im Fenster 90 Tage zurück bis 366 Tage voraus in Vorkommen aufgelöst. Außerhalb dieses Fensters ist die Belegung nicht bestätigt. Haarvinci erzeugt keine Wiederholungsreihen; in eine Reihe umgewandelte eigene Termine bleiben Konflikte. Ganztagsereignisse werden als Berliner Kalendertage berücksichtigt, UTC für Dauervergleiche, Europe/Berlin für Anzeige und Eingabe.

## Technische Grenzen und offizielle Grundlagen

Die API bietet keinen Google-Server-ETag, keine transaktionale gemeinsame Speicherung mit der lokalen Django-Datenbank und keine Garantie für Google-Synchronisation oder den Erhalt von Provider-IDs/App-Metadaten nach Kontoneueinrichtung. Diese Unsicherheiten werden durch dauerhafte Absicht, eindeutigen Marker, Vergleichsstand und sichere Unterbrechung behandelt. Bei vollständigem Verlust beider Marker ist manuelle Prüfung erforderlich; automatisches Raten wäre unzuverlässig. Kalenderanbieter und verwaltete Arbeitsprofile können die Verfügbarkeit begrenzen. Ein vom System synchronisierter, beschreibbarer Google-Kalender auf einem Pixel ist der vorgesehene Weg. Ein bloßes Öffnen des Google-Terminformulars wird nicht als Synchronisierung verwendet.

Offizielle Dokumentation/Quellen, geprüft bei Entwicklung:

- [Android Calendar Provider](https://developer.android.com/identity/providers/calendar-provider): Berechtigungen, Calendars, Events, Instances.
- [CalendarContract](https://developer.android.com/reference/android/provider/CalendarContract), [Events](https://developer.android.com/reference/android/provider/CalendarContract.Events), [Instances](https://developer.android.com/reference/android/provider/CalendarContract.Instances).
- [Offizieller AOSP-Vertrag CalendarContract.java](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/main/core/java/android/provider/CalendarContract.java) und [CalendarProvider2.java](https://android.googlesource.com/platform/packages/providers/CalendarProvider/+/refs/heads/main/src/com/android/providers/calendar/CalendarProvider2.java). Da developer.android.com in dieser Cloud nicht erreichbar war, wurden die offiziellen AOSP-Dateien über die [AOSP-GitHub-Spiegelung](https://github.com/aosp-mirror/platform_frameworks_base/blob/master/core/java/android/provider/CalendarContract.java) geprüft.

Produktionscode setzt keine Sync-Adapter-Flags und schreibt keine Sync-Adapter-Felder wie `_SYNC_ID`, `SYNC_DATA` oder `DIRTY`. Nur die isolierte Instrumentierung legt fiktive lokale Testkalender mit dem dafür vorgesehenen Adapterzugang an und entfernt sie anschließend.

## Noch auf einem echten Pixel zu prüfen

1. In beiden tatsächlich verwendeten Google-Konten die gewünschten Kalender aktivieren; Berechtigungen erlauben/ablehnen/widerrufen und erneut erlauben.
2. Geschäftlich anlegen, ändern und absagen, dann im Google-Kalender auf einem zweiten Gerät prüfen. Flugmodus: lokal ändern, App beenden/neustarten, Netz wieder aktivieren, Android-Sync abwarten; keine Dubletten.
3. Den gleichen Haarvinci-Termin in Google und Haarvinci unabhängig bearbeiten: Entscheidung prüfen. Google-Löschung, Konto-Neuanmeldung, entfernte Marker und doppelt kopiertes Ereignis müssen zur sicheren Unterbrechung führen.
4. Privaten wiederkehrenden und ganztägigen Testtermin über Zeitumstellung anlegen: nur „Privat belegt“, keine Inhaltsübernahme, keinerlei Änderungen am privaten Kalender.
5. Hintergrundabgleich mit Pixels Energiesparen und gesperrtem Bildschirm prüfen. Eine App kann die Android-Sync-Ausführung nicht erzwingen.

Die Emulatorprüfung verwendet echte Calendar-Provider-Daten mit fiktiven LOCAL-Konten. Sie ersetzt **keinen** angemeldeten Google-Kontosync auf einem echten Pixel. Die frühere Anleitung `GOOGLE-KALENDER.md` beschreibt den nun inaktiven REST/OAuth-Prototyp und ist für diese Android-Testversion nicht erforderlich.
