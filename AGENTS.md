# Haarvinci

- Deutschsprachige Anwendung für Windows-PC/Laptop und optional mobile Servernutzung für Conny, Schwerpunkt Haarverlängerung/Haarverdichtung.
- Django 5.2 LTS / SQLite (Desktop), PostgreSQL 17 (Server) / serverseitige Templates. Desktop: PySide6 + Waitress. Architektur: docs/ARCHITEKTUR.md.
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

- Aktueller Schwerpunkt: eigenständige Windows-App, kein Browserstart. Siehe docs/DESKTOP.md.
- Desktop-Abhängigkeiten mit uv sync --frozen --extra desktop --group desktop-build installieren; bei uv run Extras erhalten.
- Desktop-Start: uv run --extra desktop python -m desktop_app. In der Cloud für GUI-Tests QT_QPA_PLATFORM=offscreen; Sandbox-Deaktivierung ausschließlich für den isolierten Linux-GUI-Test, nicht im ausgelieferten Programm.
- Isolierter nativer Funktionstest: python -m desktop_app --data-dir NEUER_TESTORDNER --smoke-test --test-result test-results/desktop/smoke.json. Niemals gegen produktive Daten starten.
- Windows-Build/Installer und tatsächliche installierte Desktop-App werden in .github/workflows/desktop-windows.yml geprüft. Keine Installer aus ungeprüften Builds als funktionsfähig bezeichnen.
