# Betrieb, Sicherheit und Datensicherung

## Aktueller Stand

Die vorbereitete Version ist eine lokale Entwicklungsversion mit sechs fiktiven Testkundinnen. Die Kundenverwaltung funktioniert mit PostgreSQL und Gunicorn. Ein öffentliches Hosting, Google-Anmeldung, E-Mail-Versand, automatische externe Sicherung und Zugriff von einem physischen Pixel sind noch nicht eingerichtet.

## Lokale Daten

- PostgreSQL speichert im benannten Docker-Volume `haarvinci_postgres_data`.
- Stoppen/Neustarten von App und Container löscht dieses Volume nicht.
- `docker compose down -v`, `docker volume rm` und unbedachte Bereinigung können es löschen. Diese Befehle nicht verwenden.
- `.local/backups` enthält Datenbanksicherungen. Sie sind absichtlich nicht in Git.
- `.env` enthält das lokale Datenbankpasswort und den Django-Schlüssel; `.local/demo-access.txt` das einmalig generierte Testpasswort. Nicht weitergeben, veröffentlichen oder in Git aufnehmen.
- Ein Serverneustart ist kein Datenverlust; eine zerstörte Maschine oder verlorenes Volume kann ohne externe Sicherung einer sein.

## Sicherung

`scripts/start.sh` erstellt bei jedem Start eine geprüfte Sicherung, wenn an diesem UTC-Tag noch keine gültige existiert. Während die App läuft, prüft der betreute Startprozess jede Stunde, ob eine neue Tagessicherung nötig ist; Fehler werden im Terminal protokolliert und nach fünf Minuten erneut versucht. Beim Beenden werden Webserver und Sicherungssteuerung gemeinsam gestoppt. Für Sicherungen auch bei gestoppter App kann unter Linux zusätzlich **täglich** ein Eintrag über `crontab -e` eingerichtet werden (Beispiel für 03:00 Uhr in der Zeitzone des Servers; für Conny Europe/Berlin wählen):

```cron
0 3 * * * cd /absoluter/pfad/haarvinci && /absoluter/pfad/zu/uv run --frozen python scripts/backup.py backup >> .local/backup.log 2>&1
```

Im vorbereiteten Cloud-System ist die Sicherungssteuerung Teil des laufenden App-Startprozesses; ein zusätzlicher systemweiter Cron-Zeitplan ist nicht installiert. Eine Veröffentlichung durch die Cloud-Oberfläche ist ebenfalls keine laufende Datensicherung.

Manuell:

```bash
uv run python scripts/backup.py backup
```

Das Werkzeug verwendet PostgreSQL `pg_dump` im Custom-Format mit exportiertem konsistentem Snapshot. Manifest und Dump beziehen sich auf denselben Datenstand, auch bei parallelen Schreibzugriffen. Es erstellt Dateien mit restriktiven Rechten, prüft SHA-256 und die Lesbarkeit des PostgreSQL-Archivs und löscht misslungene neue Ausgaben. Alte Sicherungen werden nicht automatisch gelöscht. Behalte beispielsweise tägliche Kopien für 14 Tage und monatliche Kopien für ein Jahr, angepasst an den späteren Bedarf. Ein Prüfsummenfehler ist ein Fehler, kein Anlass ihn zu ignorieren.

Die Archivdatei enthält Kundendaten und Passwort-Hashes. SHA-256 erkennt Beschädigungen, ersetzt aber keine Verschlüsselung oder Herkunftsprüfung. Kopiere `.dump` **und** `.json` regelmäßig auf einen getrennten, verschlüsselten Speicher. Sichere auch die `.env` separat verschlüsselt, mit begrenztem Zugriff; ein späterer Wechsel des Django-Schlüssels meldet bestehende Sitzungen ab.

Für eine extern verwaltete Datenbank ist dieses lokale Docker-Werkzeug bewusst gesperrt. Dort die geprüften Sicherungs-/Wiederherstellungsfunktionen des Datenbankanbieters mit automatischer täglicher Sicherung, Verschlüsselung, Aufbewahrung und möglichst zeitpunktbezogener Wiederherstellung verwenden. Erfolgreiche Sicherungsjobs überwachen und regelmäßig eine Wiederherstellung in eine getrennte Datenbank testen.

## Wiederherstellungsprobe

```bash
uv run python scripts/backup.py restore-test .local/backups/DEINE-SICHERUNG.dump
```

Es wird eine neue temporäre Datenbank angelegt. PostgreSQL spielt das gesamte Archiv mit Fehlerabbruch zurück. Das Werkzeug vergleicht die Anzahl der Datensätze in allen Tabellen mit dem Manifest und entfernt nur die von ihm angelegte temporäre Datenbank. Die eigentliche Datenbank bleibt unangetastet.

## Tatsächlich wiederherstellen, ohne die bestehende Datenbank zu überschreiben

1. App im Terminal mit `Strg+C` anhalten. PostgreSQL weiterlaufen lassen. Falls es eine frische Maschine ist, zuerst `bash scripts/setup.sh` ausführen, **keine neuen Demo-Daten anlegen**.
2. Eine geprüfte Sicherung in eine **noch nicht vorhandene** Zieldatenbank spielen:

   ```bash
   uv run python scripts/backup.py restore .local/backups/DEINE-SICHERUNG.dump --database haarvinci_recovered
   ```

3. Nur bei erfolgreicher Wiederherstellung in der lokalen `.env` `POSTGRES_DB=haarvinci_recovered` setzen. Andere Werte erhalten. Das Werkzeug unterstützt absichtlich kein Überschreiben einer bestehenden Zieldatenbank. Bei einem misslungenen Versuch die Ursache prüfen und für einen neuen Versuch einen anderen Namen verwenden.
4. `bash scripts/start.sh` ausführen. Compose übernimmt den geänderten Datenbanknamen; die bestehende Datenbank bleibt zur Rückkehr erhalten. Mit dem Zugang aus dem Sicherungszeitpunkt anmelden und Kundenakten prüfen.
5. Erst nach unabhängiger Prüfung und neuer externer Sicherung alte Datenbanken gezielt bereinigen.

Für Code und Schema einen zur Sicherung passenden Git-Stand verwenden. Nach erfolgreicher Rückspielung zunächst `uv run python manage.py migrate --plan` prüfen und notwendige Migrationen vor dem Start ausführen.

## Passwort verloren

Auf dem vertrauenswürdigen Server im Projektordner:

```bash
uv run python manage.py changepassword conny
```

Django fragt das neue Passwort verdeckt im Terminal ab. Es gehört weder in einen Shell-Befehl noch in Chat oder Git. Nach zu vielen Fehlversuchen 15 Minuten warten oder als Administrator gezielt `uv run python manage.py axes_reset_username conny` ausführen. Keine öffentliche Selbstregistrierung und kein ungesicherter Passwort-Reset.

## Vor Nutzung echter Kundendaten über das Internet

- HTTPS auf einer eigenen Adresse, Zertifikat automatisch erneuern; Webserver intern binden.
- `DJANGO_DEBUG=false`, einen eigenen zufälligen `DJANGO_SECRET_KEY` mit mindestens 50 Zeichen und explizite `DJANGO_ALLOWED_HOSTS` setzen.
- `DJANGO_CSRF_TRUSTED_ORIGINS=https://DEINE-DOMAIN` setzen, keine Wildcards.
- Hinter einem eigenen vertrauenswürdigen Reverse Proxy `DJANGO_TRUST_PROXY=true` setzen. Der Proxy muss eingehende `X-Forwarded-Proto`-Header entfernen/überschreiben und selbst korrekt setzen; direkter Zugriff auf Gunicorn bleibt gesperrt.
- Externes PostgreSQL über `DATABASE_URL` mit validiertem TLS-Zertifikat verbinden, idealerweise `sslmode=verify-full` und passender CA-Konfiguration. Zugang über den Secret-Speicher des Hosters einrichten, keine Zugangsdaten im Quellcode.
- Einen eigenen Produktivzugang erstellen (`uv run python manage.py createsuperuser`), keinen Demo-Bestand übernehmen. Eine neue Produktionsdatenbank verwenden. Die normale App erfordert keine Superuser-Rechte; den Zugang anschließend organisatorisch auf den nötigen Benutzer beschränken.
- App als betreuten Dienst starten, zum Beispiel Gunicorn hinter einem HTTPS-Proxy; im Container/auf dem Server nicht den Django-Entwicklungsserver verwenden. `uv run python manage.py collectstatic --noinput` nach Aktualisierungen ausführen.
- `uv run python manage.py check --deploy --fail-level WARNING` mit der echten Produktionskonfiguration ausführen.
- Datenbank nicht öffentlich freigeben; eigene Laufzeitrolle mit minimalen Rechten und separate Migrations-/Sicherungsrolle verwenden. Lokales Compose verwendet der Einfachheit halber eine privilegierte PostgreSQL-Entwicklungsrolle und ist nicht die Produktionsvorlage.
- Sicherungen täglich außerhalb der App-Maschine verschlüsselt speichern, Fehler melden, Wiederherstellung testen. `/bereit/` prüft Datenbankerreichbarkeit für die Überwachung, liefert keine Zugangsdaten.
- Löschfristen, Auskunft/Export, Datenschutzhinweise und ggf. Auftragsverarbeitung mit dem Hoster fachlich klären. Diese erste Etappe hat Export, aber noch keine endgültige Kundenlöschung.
- Geheimnisse regelmäßig wechseln; Sicherheitsupdates für Django, Python und PostgreSQL einplanen. Tests und Wiederherstellungsprobe nach Updates ausführen.

Die aktuelle lokale Prüfung bestätigt keine Veröffentlichung und keine Erreichbarkeit auf Connys realem Pixel. Die reguläre Nutzung auf dem Pixel beginnt erst mit der geprüften HTTPS-Installation. Google-Kalender-OAuth und externe API-Schlüssel werden in Phase 1 nicht benötigt.
