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
- Daten im Backend speichern: SQLite für Desktop/Android, PostgreSQL für den Server. Keine Kundenakten im LocalStorage/Service-Worker-Cache ablegen.
- Git sichert Code. Backup/Wiederherstellung separat gemäß docs/BETRIEB.md testen.

- Aktueller Schwerpunkt: eigenständige Windows-App, kein Browserstart. Siehe docs/DESKTOP.md.
- Desktop-Abhängigkeiten mit uv sync --frozen --extra desktop --group desktop-build installieren; bei uv run Extras erhalten.
- Desktop-Start: uv run --extra desktop python -m desktop_app. In der Cloud für GUI-Tests QT_QPA_PLATFORM=offscreen; Sandbox-Deaktivierung ausschließlich für den isolierten Linux-GUI-Test, nicht im ausgelieferten Programm.
- Isolierter nativer Funktionstest: python -m desktop_app --data-dir NEUER_TESTORDNER --smoke-test --test-result test-results/desktop/smoke.json. Niemals gegen produktive Daten starten.
- Windows-Build/Installer und tatsächliche installierte Desktop-App werden in .github/workflows/desktop-windows.yml geprüft. Keine Installer aus ungeprüften Builds als funktionsfähig bezeichnen.

- Android ist zusätzlich autorisiert: eigenständige APK für Connys Pixel, siehe docs/ANDROID.md. Kein externer Server als Voraussetzung für diese Variante.
- Android-Quellen unter android/. Gemeinsamen Kern mit python android/prepare_sources.py explizit bereitstellen; generierte Kopien nicht bearbeiten oder committen.
- Android-Abhängigkeiten aus uv.lock mit python android/refresh_requirements.py ableiten; Paket-Hashes und Gradle-Prüfsummen erhalten.
- Android-Kern: uv run --extra android python tests/android_runtime_smoke.py. APK-Bau und Installation werden in .github/workflows/android.yml auf einem echten Android-Emulator geprüft.
- Nur eine erfolgreich installierte und funktional geprüfte APK als lauffähig ausgeben. Entwicklungs- und Freigabesignierung unterscheiden. Keine Signierschlüssel in Git/Chat.
- Android-Backupformat bleibt mit Windows kompatibel; keine Synchronisierung zwischen Geräten behaupten.

- Android 0.4 erweitert Kunden um optionale Haarprofile und das kundenbezogene Fachmodul `extensions`. Keine Lager-/Zahlungs-/Behandlungsverwaltung hinzufügen. Details: docs/EXTENSIONS.md.
- Extensions-Preise sind Decimal-Gesamtpreise, Mengen beziehen sich auf die Position. Jede Abfrage über customer__owner begrenzen; Kundenzuordnung nie aus POST übernehmen.
- Positionsänderung und Historienereignis in derselben Transaktion speichern. Versionsprüfung auch bei bestätigter Löschung erhalten; die Historien-Momentaufnahme bleibt danach bestehen.
- Mobile Oberflächenprüfung: python tests/extensions_browser_smoke.py bei lokal laufender Test-App. Nur fiktive Daten, keine echten Besuche aus Extensions-Anzahl ableiten.
