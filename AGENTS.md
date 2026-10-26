# Haarvinci

- Deutschsprachige, mobile Anwendung für Conny, Schwerpunkt Haarverlängerung/Haarverdichtung.
- Django 5.2 LTS / PostgreSQL 17 / serverseitige Templates. Architektur: docs/ARCHITEKTUR.md.
- Bestehenden Checkout verwenden. Cloud-Aufgaben sind isoliert; ohne ausdrücklichen Wunsch keine Git-Worktrees anlegen.
- Phase 1 ist Kundenverwaltung. Andere Module nur bei ausdrücklich erweitertem Auftrag implementieren.
- Ausschließlich fiktive Daten während Entwicklung/Tests. Keine Geheimnisse, Sicherungen oder `.env` in Git/Chat ausgeben.
- Jede Kundenabfrage und Änderung auf die Eigentümerin begrenzen. CSRF, sichere Passworthashes und serverseitige Validierung erhalten.
- Änderungen an Geschäftsabläufen in Dienste kapseln; kein Geschäftsverhalten in Templates verstecken.
- Einrichtung: bash scripts/setup.sh. Demo bei Bedarf ausdrücklich: uv run python manage.py init_demo.
- Start: bash scripts/start.sh; prüfe intern /bereit/ und danach eine geschützte Funktion mit Anmeldung.
- Prüfen: uv run python manage.py test tests; uv run ruff check .; uv run python manage.py makemigrations --check --dry-run.
- Browser: uv run python tests/browser_smoke.py bei laufender App. Playwright oder System-Chromium erforderlich.
- Daten bleiben in PostgreSQL; keine Kundenakten im LocalStorage/Service-Worker-Cache ablegen.
- Git sichert Code. Backup/Wiederherstellung separat gemäß docs/BETRIEB.md testen.
