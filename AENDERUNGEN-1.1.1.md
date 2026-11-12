# HaarVinci Signature 1.1.1

Instagram und Google-Bewertungen sind jetzt über zwei große Buttons direkt im oberen Bereich erreichbar. Der Google-Button springt zur Bewertungssektion. Dort erscheinen drei kurze Auszüge aus den vom Nutzer bereitgestellten veröffentlichten Google-Rezensionen von EmmA N., Henry und Serpil B., jeweils mit ihrer individuellen Fünf-Sterne-Bewertung. Große, getrennte Buttons führen zum Google-Profil und zur Bewertungsabgabe; Instagram ist zusätzlich im Vertrauensbereich verlinkt.

Die Auszüge sind als Auswahl gekennzeichnet. Es werden weder ein unbelegter Gesamtdurchschnitt noch eine Anzahl oder automatische Aktualisierung behauptet. Der unveröffentlichte Beitrag, medizinische Angaben und fremde Screenshots werden nicht übernommen. Quellen und Wortlaut stehen in `content/review-excerpts.json`.

Timo Bockhorn hat die acht Vorher-Nachher-Fotos ausdrücklich freigegeben. `content/media-approval.json` dokumentiert diese aktuelle Anweisung und ersetzt die alten Sperrvermerke. Alle vier Paare haben `websiteApproved: true`. Nach Lieferung der Originaldateien prüft `npm run import:signature -- PFAD` alle acht Hashes, übernimmt die Originale und aktiviert die vorgegebene Paarzuordnung für den normalen Build. Keine weitere Foto-Freigabe ist erforderlich.

Die Original-JPGs sind hier weiterhin nicht als Dateien vorhanden. Das zugängliche ältere ZIP enthält sie nicht. Deshalb zeigt diese Ausgabe noch die vorhandenen echten Reel-Standbilder und keine vier neuen Vorher-Nachher-Paare. Der Import und die Darstellung sind mit getrennten, ausdrücklich fiktiven Testflächen geprüft; diese Testbilder sind nicht Teil der Vorschau.

Der Vorschau-Download ist kein Livegang. Die bestehenden Rechtstext- und Livegang-Sperren bleiben erhalten. Android-, Windows- und Django-Anwendung sowie IONOS, DNS und E-Mail bleiben unberührt.
