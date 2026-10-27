> Historischer OAuth-/REST-Prototyp aus 0.5.0. Für Android ab 0.5.1 ist keine Einrichtung nach dieser Anleitung nötig. Die aktive Verbindung verwendet [Android-Gerätekalender](ANDROID-GERAETEKALENDER.md).

# Google Kalender verbinden – Vorbereitung für Haarvinci 0.5

**Du kannst den lokalen Kalender sofort ohne diese Einrichtung verwenden.** Google ist optional. Die App zeigt eine fehlende Verbindung ausdrücklich an. Bis zur Auslieferung wurden API-Antworten, Fehlerfälle, OAuth-Übergabe und Konflikte automatisiert simuliert; eine echte Google-Anmeldung, echte Kalenderberechtigungen und ein echter Internet-Abgleich wurden mangels eigener Google-Konfiguration noch nicht geprüft.

## Was bereits implementiert ist

- Getrennte geschäftliche und private Verbindungen, auch in unterschiedlichen Google-Konten.
- Anmeldung im Systembrowser, anschließend Rückkehr zur App und native Kalenderauswahl.
- Offizielle Google Calendar API v3. Geschäftlich werden **eigene** Google-Kalender angeboten. Haarvinci-Termine werden übertragen, geändert, aus Google zurückgelesen und bei Absage abgeglichen. Vorhandene fremde Google-Termine werden als schreibgeschützte Belegung berücksichtigt; eine Kundin wird nie anhand eines Titels geraten.
- Privat wird ausschließlich `freeBusy` abgefragt. Es gibt keine lokale Speicherung privater Ereignistitel, Beschreibungen oder Teilnehmer und keine Schreibzugriffe auf den privaten Kalender.
- Feste Ereignis-IDs und Zuordnung, bedingte Änderungen mit ETag, Offline-Outbox, Erkennung beidseitiger Änderungen und bestätigte Konfliktentscheidungen. Kein stilles Überschreiben bei unklaren Netzwerkergebnissen.
- Android-KeyStore/AES-GCM für Tokens und Anmeldebeweise, gebunden an Eigentümerin und Verbindungs-UUID. Keine Tokens in Kunden-Datenbank, JSON-Export, `.haarvinci`-Sicherung oder Git.
- Android WorkManager für Internet-bedingte Aufträge nach Änderungen und periodische Wiederholung (mindestens 15 Minuten). Android bestimmt die tatsächliche Ausführung bei geschlossener App und kann sie wegen Energiesparregeln verschieben. Das ist keine sekundengenaue Zusage. Ohne eingerichtete Verbindung werden keine regelmäßigen Google-Aufträge eingeplant.

## Warum ein kleiner Anmeldedienst vorgesehen ist

Diese Variante verwendet einen **optionalen eigenen HTTPS-Anmeldedienst** (`google_broker`), damit der Google-Login im Systembrowser erfolgt und ein vertrauliches Google-Client-Geheimnis ausschließlich auf einem Server liegt. Die Android-App bleibt für ihre eigentlichen Daten eine eigenständige Offline-App. Der Dienst bekommt keine Kundenakten oder privaten Kalenderinhalte; nach der Anmeldung fragt das Pixel die Calendar API direkt ab.

Der Dienst verwendet einen Google-OAuth-Client vom Typ **Webanwendung**, die offizielle Bibliothek `google-auth-oauthlib`, OAuth-State und PKCE. Der Browser-Redirect führt zu seiner eigenen HTTPS-Adresse. Die App erhält die Tokens über eine kurzlebige, einmalige und zusätzlich durch ihren eigenen PKCE-Beweis geschützte Übergabe. Temporäre Tokens auf dem Dienst sind verschlüsselt und höchstens zehn Minuten abrufbar. Dauerhaft speichert der Dienst nur die Registrierung eines Gerätes mit einem Hash des Gerätebeweises. Er speichert keine langfristigen Google-Refresh-Tokens. Refresh-Anfragen benötigen den auf dem Pixel verschlüsselt gespeicherten Gerätebeweis und Refresh-Token; das Client-Geheimnis bleibt auf dem Dienst.

Der Anmeldedienst wurde **noch nicht öffentlich gehostet**. Es wurden keine kostenpflichtigen Dienste gebucht oder Google-Projekte angelegt. Für eine echte Google-Verbindung fehlen deshalb noch die folgenden manuellen Schritte.

## Schritt 1: Google-Cloud-Projekt vorbereiten

1. In der [Google Cloud Console](https://console.cloud.google.com/) mit dem Konto öffnen, das das App-Projekt verwalten soll. Ein Projekt für den Haarvinci-Test anlegen oder ein eigenes vorhandenes Projekt auswählen.
2. Unter **APIs und Dienste → Bibliothek** die **Google Calendar API** aktivieren.
3. Unter **Google Auth Platform** bzw. **OAuth-Zustimmungsbildschirm** die App beschreiben. Für persönliche Google-Konten den externen Testbetrieb verwenden und die beteiligten geschäftlichen und privaten Konten als **Testnutzer** eintragen. Je nach Console-Version heißen die Menüpunkte etwas anders.
4. Die benötigten Berechtigungen eintragen. Haarvinci fordert sie getrennt je Verbindung an:
   - Beide Rollen: `https://www.googleapis.com/auth/calendar.calendarlist.readonly`
   - Geschäftlich: `https://www.googleapis.com/auth/calendar.events.owned`
   - Privat: `https://www.googleapis.com/auth/calendar.events.freebusy`
5. Im Testbetrieb können Google-Refresh-Tokens für Kalenderberechtigungen nach sieben Tagen ablaufen. Die App verlangt dann eine erneute Anmeldung. Vor späterer Übergabe/Veröffentlichung müssen Googles Anforderungen an den Freigabestatus und gegebenenfalls die App-Prüfung separat erfüllt werden.

Es werden weder Google-Passwörter noch Service-Account-Schlüssel benötigt. Für einen freigegebenen Kalender, den das gewählte Konto nicht selbst besitzt, wird in dieser ersten geschäftlichen Integration bewusst keine weitergehende Schreibberechtigung verlangt.

## Schritt 2: HTTPS-Adresse und OAuth-Client

Du brauchst einen eigenen, vertrauenswürdigen HTTPS-Host, beispielsweise `https://anmeldung.deine-domain.de`. Eine lokale Adresse aus der Codex-Cloud ist vom privaten Pixel aus nicht erreichbar und genügt dafür nicht.

1. Unter **Anmeldedaten / Clients → OAuth-Client erstellen** den Typ **Webanwendung** auswählen. Es wird für diese konkrete Broker-Variante kein Android-OAuth-Client und kein in die APK eingebautes Client-Geheimnis verwendet.
2. Als autorisierte Weiterleitungs-URI **exakt** `https://anmeldung.deine-domain.de/oauth/google/callback/` eintragen, einschließlich abschließendem Schrägstrich.
3. Client-ID und Client-Geheimnis im privaten Konfigurationsbereich des Anmeldeservers speichern. Niemals in Chat, Git, APK oder in die Haarvinci-Oberfläche kopieren.

## Schritt 3: Anmeldedienst betreiben

Dieser Abschnitt betrifft einen eigenen Server bzw. einen verwalteten Python-Host. Er wird nicht auf dem Pixel ausgeführt. Eine getrennte Installation/eigene Datenbank für den Dienst verwenden; nicht mit der Kundendatenbank eines Rechners verwechseln.

Erforderlich sind Python 3.12, uv, eine kleine PostgreSQL-Datenbank und ein HTTPS-Reverse-Proxy oder ein verwalteter Host mit HTTPS. Im privaten Umgebungs-/Secret-Bereich setzen:

| Variable | Inhalt |
| --- | --- |
| `DJANGO_SETTINGS_MODULE` | `google_broker.settings` |
| `GOOGLE_BROKER_DJANGO_SECRET` | Zufälliger eigener Schlüssel mit mindestens 50 Zeichen |
| `GOOGLE_CLIENT_ID` | Eigene Web-OAuth-Client-ID |
| `GOOGLE_CLIENT_SECRET` | Eigenes Client-Geheimnis, ausschließlich serverseitig |
| `GOOGLE_HANDOFF_KEY` | Separater Fernet-Schlüssel für kurzlebige Tokenübergaben |
| `GOOGLE_REDIRECT_URI` | Die exakt bei Google eingetragene HTTPS-Callback-Adresse |
| `GOOGLE_BROKER_HOSTS` | Eigener Hostname ohne `https://`, keine Wildcards |
| `GOOGLE_BROKER_DATABASE_URL` | Eigene PostgreSQL-Verbindungsadresse des Dienstes |
| `GOOGLE_BROKER_TRUST_PROXY` | Nur `true`, wenn der eigene HTTPS-Proxy `X-Forwarded-Proto` zuverlässig selbst setzt |

Neue Schlüssel auf dem eigenen Server erzeugen und unmittelbar privat ablegen. Die Befehle geben sie im eigenen Terminal aus; diese Ausgaben nicht weitergeben:

```bash
uv sync --frozen --no-dev --extra google-broker
uv run --no-dev --extra google-broker python -c "import secrets; print(secrets.token_urlsafe(64))"
uv run --no-dev --extra google-broker python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Nachdem die privaten Variablen gesetzt sind:

```bash
uv run --frozen --no-dev --extra google-broker python manage.py migrate
uv run --frozen --no-dev --extra google-broker gunicorn google_broker.wsgi:application --bind 127.0.0.1:8080 --workers 2 --timeout 45
```

Den internen HTTP-Port ausschließlich hinter dem eigenen HTTPS-Proxy betreiben. Zugriffslimits auf `/mobil/` und `/oauth/` setzen, beispielsweise wenige Anfragen pro Sekunde und eine kleine Burst-Reserve. Anfragekörper auf 16 KiB beschränken. Keine Request-Bodies, Authorization-Header oder Querystrings protokollieren: OAuth-Callbacks enthalten kurzlebige Codes. Bei Nginx für ein eigenes Access-Log nur `$uri` statt `$request_uri` verwenden; Gunicorn-Zugriffsprotokolle nicht mit Querystrings aktivieren. Abgelaufene Übergaben werden bei weiteren Zugriffen entfernt; zusätzlich lässt sich die Bereinigung regelmäßig ausführen:

```bash
uv run --frozen --no-dev --extra google-broker python manage.py shell -c "from google_broker.views import cleanup; cleanup()"
```

Die Broker-Routen sind nur unter dieser eigenen Einstellung aktiv. Die normale Haarvinci-App stellt keine öffentlichen Token-Endpunkte bereit. Es wird keine unsichere HTTP- oder Zertifikatsausnahme für den Android-Login eingebaut.

## Schritt 4: Auf dem Pixel verbinden

1. In Haarvinci anmelden und **Kalender → Google-Verbindungen → Anmeldedienst einrichten** öffnen.
2. Nur die Basisadresse des eigenen HTTPS-Dienstes eintragen, etwa `https://anmeldung.deine-domain.de`, ohne Pfad. Keine Google-Zugangsdaten eingeben.
3. Bei **Geschäftlich → Google verbinden** die Anmeldung im Systembrowser durchführen. Das gewünschte geschäftliche Google-Konto auswählen und die Berechtigungen prüfen.
4. Nach Abschluss des Browserdialogs zurück zur Haarvinci-App wechseln. Falls Android die App neu gestartet hat, erneut in Haarvinci anmelden und **Verbindung abschließen** wählen. Den gewünschten **eigenen** geschäftlichen Kalender im nativen Auswahlfenster auswählen.
5. **Privat → Google verbinden** gesondert durchführen. Hier darf ein anderes Google-Konto ausgewählt werden. Anschließend den privaten Kalender auswählen.
6. **Jetzt synchronisieren** wählen. Erst ein tatsächliches Abgleichdatum bestätigt einen erfolgreichen API-Abruf. Fehlende Berechtigung, Netzfehler und Konflikte bleiben sichtbar.

Pro Rolle wird zunächst ein Kalender verbunden. Beide Rollen dürfen in demselben Konto liegen, aber der geschäftliche und private **Kalender müssen verschieden sein**, damit private Inhalte zuverlässig auf Belegt-Zeiten begrenzt bleiben. Nach einer ersten geschäftlichen Übertragung wird ein Wechsel in einen anderen Zielkalender nicht automatisch durchgeführt; ein versehentliches Kopieren bereits zugeordneter Termine soll vermieden werden.

**Verbindung trennen** entfernt die lokale Verbindung und ihre Tokenablage; Google-Termine werden nicht verändert oder gelöscht. Bei fehlendem Internet kann eine verwaiste Geräte-Registrierung auf dem eigenen Dienst bestehen bleiben, die keine Google-Tokens enthält. Eine vollständige Google-Freigabe kann zusätzlich in den Google-Kontoeinstellungen entfernt werden; das kann andere Rollen desselben Google-Kontos betreffen.

## Schritt 5: Echten Abgleich mit fiktiven Terminen prüfen

1. In einem eigenen leeren geschäftlichen Testkalender einen Haarvinci-Termin übertragen; mehrmals synchronisieren und sicherstellen, dass nur ein Google-Ereignis existiert.
2. Den Termin in Haarvinci verschieben, abgleichen und die Google-Zeit prüfen.
3. Zeit oder Notiz des **von Haarvinci angelegten** Termins in Google ändern, abgleichen und den übernommenen Stand in Haarvinci prüfen.
4. Beide Seiten vor einem Abgleich verändern. Die App muss einen Konflikt zeigen; beide Stände prüfen und ausdrücklich entscheiden. Keine automatische Zuordnung fremder Termine anhand von Namen erwarten.
5. Einen bestehenden fremden geschäftlichen Google-Termin anlegen: er erscheint als Belegung, ohne dass Haarvinci ihn verändert.
6. In einem **getrennten privaten Testkalender** einen Termin mit einem markanten privaten Titel erstellen. In Haarvinci darf ausschließlich „Privat belegt“ erscheinen. Die App darf diesen Google-Termin weder bearbeiten noch löschen.
7. In Haarvinci einen eigenen Termin absagen. Nach dem Abgleich muss das eigene Google-Ereignis abgesagt/gelöscht sein; fremde und private Ereignisse müssen erhalten bleiben. Die Absage zählt nicht als Besuch.
8. Flugmodus aktivieren, lokal bearbeiten, App neu starten und wieder Internet zulassen. Den sichtbaren ausstehenden Stand und den späteren tatsächlichen Abgleich prüfen. Android-Hintergrundlimits berücksichtigen.

Solange diese Schritte nicht mit den eigenen Konten durchgeführt wurden, ist die Integration technisch vorbereitet und automatisiert geprüft, aber **nicht als mit echten Google-Konten abgenommen** zu bezeichnen.

## Referenzen und API-Basis

- [Google OAuth 2.0 für Webserver-Anwendungen](https://developers.google.com/identity/protocols/oauth2/web-server)
- [Google OAuth 2.0 für native Apps](https://developers.google.com/identity/protocols/oauth2/native-app)
- [Google Calendar API – Berechtigungen](https://developers.google.com/workspace/calendar/api/auth)
- [Google Calendar API – FreeBusy](https://developers.google.com/workspace/calendar/api/v3/reference/freebusy/query)
- [Google Calendar API – bedingte Änderungen](https://developers.google.com/workspace/calendar/api/guides/version-resources)
- [Android Keystore](https://developer.android.com/privacy-and-security/keystore)
- [Android WorkManager](https://developer.android.com/develop/background-work/background-tasks/persistent)

Die verwendeten Calendar-v3-Endpunkte, Scopes und Methoden wurden mit der offiziellen Google-API-Discovery-Definition, Revision **20260925**, im [Google-Repository](https://github.com/googleapis/google-api-python-client/blob/main/googleapiclient/discovery_cache/documents/calendar.v3.json) abgeglichen. Die eingebundene offizielle OAuth-Bibliothek und alle Abhängigkeiten sind in `uv.lock` festgelegt. Der echte Konto- und Berechtigungstest bleibt davon getrennt.
