import argparse
import logging
import os
import secrets
import subprocess
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PySide6.QtCore import (
    QLibraryInfo,
    QLocale,
    QLockFile,
    QStandardPaths,
    QTimer,
    QTranslator,
    QUrl,
)
from PySide6.QtGui import QAction, QDesktopServices, QIcon, QKeySequence
from PySide6.QtWebEngineCore import (
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineSettings,
    QWebEngineUrlRequestInterceptor,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QFileDialog, QMainWindow, QMessageBox

from . import __version__
from .server import start_backend, stop_backend
from .storage import (
    BackupError,
    create_backup,
    daily_backup,
    installation_secret,
    restore_backup,
    validate_backup,
)

ROOT = Path(__file__).resolve().parent.parent


class LocalOnlyInterceptor(QWebEngineUrlRequestInterceptor):
    def __init__(self, origin, token, parent):
        super().__init__(parent)
        self.origin = origin
        self.token = token.encode("ascii")

    def interceptRequest(self, info):
        url = info.requestUrl()
        if f"{url.scheme()}://{url.host()}:{url.port()}" == self.origin:
            info.setHttpHeader(b"X-Haarvinci-Desktop", self.token)
        elif url.scheme() not in {"data", "about"}:
            info.block(True)


class LocalPage(QWebEnginePage):
    def __init__(self, profile, origin, parent):
        super().__init__(profile, parent)
        self.origin = origin

    def acceptNavigationRequest(self, url, navigation_type, is_main_frame):
        if f"{url.scheme()}://{url.host()}:{url.port()}" == self.origin:
            return True
        if url.toString() == "about:blank":
            return True
        if (
            navigation_type == QWebEnginePage.NavigationType.NavigationTypeLinkClicked
            and url.scheme() in {"tel", "mailto"}
        ):
            QDesktopServices.openUrl(url)
        return False

    def createWindow(self, window_type):
        return None


class DesktopWindow(QMainWindow):
    def __init__(self, origin, token, data_dir):
        super().__init__()
        self.data_dir = data_dir
        self.origin = origin
        self.pending_restore = None
        self.setWindowTitle("Haarvinci · Connys Kundenbuch")
        self.setWindowIcon(QIcon(str(ROOT / "static/img/brand.svg")))
        self.resize(1360, 900)
        self.setMinimumSize(900, 650)
        self.view = QWebEngineView(self)
        self.profile = QWebEngineProfile(self)  # Sitzung ohne dauerhafte Cookies/Browser-Cache.
        self.profile.setHttpAcceptLanguage("de-DE,de;q=0.9")
        self.interceptor = LocalOnlyInterceptor(origin, token, self.profile)
        self.profile.setUrlRequestInterceptor(self.interceptor)
        self.page = LocalPage(self.profile, origin, self.view)
        self.view.setPage(self.page)
        self.page.settings().setFontFamily(
            QWebEngineSettings.FontFamily.SansSerifFont,
            "Segoe UI" if os.name == "nt" else "DejaVu Sans",
        )
        self.page.settings().setFontFamily(
            QWebEngineSettings.FontFamily.StandardFont,
            "Segoe UI" if os.name == "nt" else "DejaVu Sans",
        )
        self.page.settings().setAttribute(
            QWebEngineSettings.WebAttribute.LocalStorageEnabled, False
        )
        self.page.settings().setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, False
        )
        self.page.settings().setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, False
        )
        self.profile.downloadRequested.connect(self.download)
        self.setCentralWidget(self.view)
        self._menus()
        self.page.loadFinished.connect(self.update_data_actions)
        self.backup_timer = QTimer(self)
        self.backup_timer.setInterval(60 * 60 * 1000)
        self.backup_timer.timeout.connect(self.automatic_backup)
        self.backup_timer.start()
        self.view.setUrl(QUrl(origin + "/"))

    def action(self, menu, title, callback, shortcut=None):
        action = QAction(title, self)
        action.triggered.connect(callback)
        if shortcut:
            action.setShortcut(shortcut)
        menu.addAction(action)
        return action

    def _menus(self):
        files = self.menuBar().addMenu("&Datei")
        self.backup_action = self.action(
            files, "Datensicherung erstellen …", self.save_backup, "Ctrl+Shift+S"
        )
        self.backup_action.setEnabled(False)
        self.restore_action = self.action(
            files, "Datensicherung wiederherstellen …", self.choose_restore
        )
        self.restore_action.setEnabled(False)
        self.action(
            files,
            "Datenordner öffnen",
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.data_dir))),
        )
        files.addSeparator()
        self.action(files, "Beenden", self.close, QKeySequence.StandardKey.Quit)
        navigate = self.menuBar().addMenu("&Kundenbuch")
        for title, route, shortcut in [
            ("Übersicht", "/", "Alt+1"),
            ("Kundinnen", "/kundinnen/", "Alt+2"),
            ("Neue Kundin", "/kundinnen/neu/", "Ctrl+N"),
            ("Mein Konto", "/konto/", "Alt+3"),
        ]:
            self.action(
                navigate,
                title,
                lambda checked=False, path=route: self.view.setUrl(QUrl(self.origin + path)),
                shortcut,
            )
        view = self.menuBar().addMenu("&Ansicht")
        self.action(
            view,
            "Vergrößern",
            lambda: self.view.setZoomFactor(min(1.8, self.view.zoomFactor() + 0.1)),
            QKeySequence.StandardKey.ZoomIn,
        )
        self.action(
            view,
            "Verkleinern",
            lambda: self.view.setZoomFactor(max(0.8, self.view.zoomFactor() - 0.1)),
            QKeySequence.StandardKey.ZoomOut,
        )
        self.action(view, "Standardgröße", lambda: self.view.setZoomFactor(1), "Ctrl+0")
        help_menu = self.menuBar().addMenu("&Hilfe")
        self.action(
            help_menu,
            "Kurzanleitung",
            lambda: QMessageBox.information(
                self,
                "Dein Haarvinci",
                "Lege beim ersten Start deinen Zugang an.\n\nUnter Kundinnen kannst du suchen, neue Akten anlegen und bestehende bearbeiten.\n\nÜber Datei → Datensicherung erstellen sicherst du alle Daten in einer Datei, zum Beispiel auf einen USB-Stick.\n\nBitte verwende in dieser ersten Testversion nur erfundene Kundendaten.",
            ),
        )
        self.action(
            help_menu,
            "Über Haarvinci",
            lambda: QMessageBox.information(
                self,
                "Haarvinci",
                f"Haarvinci {__version__} Desktop\n\nDein persönliches Kundenbuch für PC und Laptop.\nDie Daten bleiben auf diesem Computer.\n\nDie Bedienoberfläche basiert auf Qt/PySide6 (LGPLv3). Weitere Lizenzhinweise liegen im Programmordner.",
            ),
        )

    def update_data_actions(self, ok):
        def apply(authenticated):
            from django.contrib.auth import get_user_model

            self.backup_action.setEnabled(bool(authenticated))
            self.restore_action.setEnabled(
                bool(authenticated) or not get_user_model().objects.exists()
            )

        self.page.runJavaScript(
            "document.body && document.body.dataset.authenticated === 'true'", apply
        )

    def automatic_backup(self):
        try:
            daily_backup(self.data_dir)
        except Exception:
            logging.exception("Automatische lokale Sicherung fehlgeschlagen")
            QMessageBox.warning(
                self,
                "Datensicherung benötigt Aufmerksamkeit",
                "Die automatische Sicherung konnte nicht erstellt werden. Bitte prüfe den freien Speicherplatz und erstelle über Datei eine Sicherung auf einem anderen Datenträger.",
            )

    def save_backup(self):
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Alle Haarvinci-Daten sichern",
            str(Path.home() / "Haarvinci-Sicherung.haarvinci"),
            "Haarvinci-Sicherung (*.haarvinci)",
        )
        if not filename:
            return
        if not filename.lower().endswith(".haarvinci"):
            filename += ".haarvinci"
        try:
            create_backup(self.data_dir / "haarvinci.sqlite3", filename)
            QMessageBox.information(
                self,
                "Sicherung erstellt",
                "Deine Daten wurden vollständig gesichert und geprüft. Bewahre die Datei zusätzlich auf einem getrennten Datenträger auf.",
            )
        except Exception:
            logging.exception("Manuelle Sicherung fehlgeschlagen")
            QMessageBox.warning(
                self,
                "Sicherung nicht erstellt",
                "Die Sicherung konnte nicht erstellt werden. Bitte prüfe den Speicherort. Deine Kundenakten bleiben erhalten.",
            )

    def choose_restore(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Haarvinci-Sicherung auswählen",
            str(Path.home()),
            "Haarvinci-Sicherung (*.haarvinci)",
        )
        if not filename:
            return
        try:
            metadata, _ = validate_backup(filename)
        except BackupError as error:
            QMessageBox.warning(self, "Sicherung nicht verwendbar", str(error))
            return
        count = metadata["tables"]["customers_customer"]
        answer = QMessageBox.question(
            self,
            "Diesen Datenstand wiederherstellen?",
            f"Die geprüfte Sicherung enthält {count} Kundenakten.\n\nHaarvinci erstellt zuerst eine zusätzliche Sicherung des aktuellen Stands und startet anschließend mit dem gewählten Datenstand neu.\n\nMöchtest du fortfahren?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.pending_restore = filename
            self.close()

    def download(self, item):
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Kundenakte exportieren",
            str(Path.home() / item.suggestedFileName()),
            "JSON-Datei (*.json)",
        )
        if not filename:
            item.cancel()
            return
        path = Path(filename)
        item.setDownloadDirectory(str(path.parent))
        item.setDownloadFileName(path.name)
        item.accept()

    def closeEvent(self, event):
        self.backup_timer.stop()
        super().closeEvent(event)


def main():
    parser = argparse.ArgumentParser(description="Haarvinci für PC und Laptop")
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--restore-from", type=Path)
    parser.add_argument("--smoke-test", action="store_true")
    parser.add_argument("--test-result", type=Path)
    args = parser.parse_args()
    QApplication.setOrganizationName("Haarvinci")
    QApplication.setApplicationName("Haarvinci")
    QApplication.setApplicationVersion(__version__)
    QLocale.setDefault(QLocale("de_DE"))
    app = QApplication(sys.argv[:1])
    translator = QTranslator(app)
    if translator.load("qtbase_de", QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)):
        app.installTranslator(translator)
    app.setStyle("Fusion")
    data_dir = (
        args.data_dir
        or Path(
            QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)
        )
    ).resolve()
    if args.smoke_test and (not args.data_dir or not args.test_result):
        parser.error("Der isolierte Test benötigt --data-dir und --test-result.")
    if args.smoke_test and (data_dir / "haarvinci.sqlite3").exists():
        parser.error(
            "Der isolierte Test benötigt einen neuen Datenordner ohne bestehende Kundenakten."
        )
    data_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock = QLockFile(str(data_dir / "haarvinci.lock"))
    if not lock.tryLock(15000):
        QMessageBox.information(
            None,
            "Haarvinci läuft bereits",
            "Haarvinci ist bereits geöffnet. Bitte wechsle zum vorhandenen Programmfenster.",
        )
        return 1
    handler = RotatingFileHandler(
        data_dir / "haarvinci.log", maxBytes=1024**2, backupCount=3, encoding="utf-8"
    )
    logging.basicConfig(level=logging.WARNING, handlers=[handler])
    server = thread = None
    window = None
    try:
        if args.restore_from:
            restore_backup(args.restore_from, data_dir)
        secret = installation_secret(data_dir)
        if (data_dir / "haarvinci.sqlite3").exists():
            daily_backup(data_dir)
        token = secrets.token_urlsafe(48)
        server, thread, origin = start_backend(data_dir, secret, token)
        daily_backup(data_dir)
        window = DesktopWindow(origin, token, data_dir)
        window.show()
        if args.smoke_test:
            from .smoke import DesktopSmoke

            window.smoke = DesktopSmoke(window, token, args.test_result, app)
            QTimer.singleShot(1000, window.smoke.start)
        result = app.exec()
    except Exception:
        logging.exception("Haarvinci konnte nicht gestartet werden")
        if args.smoke_test:
            raise
        QMessageBox.critical(
            None,
            "Haarvinci konnte nicht starten",
            f"Die Anwendung konnte nicht geöffnet werden. Deine vorhandenen Daten wurden nicht gelöscht.\n\nHinweise findest du im Protokoll:\n{data_dir / 'haarvinci.log'}",
        )
        return 1
    finally:
        if server is not None:
            stop_backend(server, thread)
            from django.db import connections

            connections.close_all()
            try:
                daily_backup(data_dir)
            except Exception:
                logging.exception("Sicherung beim Beenden fehlgeschlagen")
        lock.unlock()
    if window and window.pending_restore:
        command = [sys.executable]
        if not getattr(sys, "frozen", False):
            command += ["-m", "desktop_app"]
        subprocess.Popen(
            [*command, "--data-dir", str(data_dir), "--restore-from", window.pending_restore]
        )
    return result
