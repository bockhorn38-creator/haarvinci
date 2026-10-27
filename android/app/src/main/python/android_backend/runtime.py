"""Derselbe Django-Fachkern innerhalb der Android-Anwendung, ohne externen Server."""

import json
import os
import secrets
import threading
from pathlib import Path

from desktop_app.storage import (
    create_backup,
    daily_backup,
    installation_secret,
    restore_backup,
    validate_backup,
)

_runtime = None
_guard = threading.RLock()


class Runtime:
    def __init__(self, data_dir, resources):
        self.data_dir = Path(data_dir)
        self.token = secrets.token_urlsafe(48)
        os.environ.update(
            {
                "DJANGO_SETTINGS_MODULE": "android_backend.settings",
                "HAARVINCI_DATA_DIR": str(self.data_dir),
                "HAARVINCI_RESOURCE_DIR": str(resources),
                "HAARVINCI_DESKTOP_SECRET": installation_secret(self.data_dir),
                "HAARVINCI_DESKTOP_TOKEN": self.token,
            }
        )
        import django

        django.setup()
        self.server = self.thread = None
        self.start()

    def start(self):
        from django.core.management import call_command
        from django.core.wsgi import get_wsgi_application
        from django.db import connections
        from waitress import create_server

        call_command("migrate", interactive=False, verbosity=0)
        connections.close_all()
        self.server = create_server(
            get_wsgi_application(),
            host="127.0.0.1",
            port=0,
            threads=4,
            ident="Haarvinci",
            clear_untrusted_proxy_headers=True,
        )
        self.thread = threading.Thread(
            target=self.server.run, name="haarvinci-android", daemon=True
        )
        self.thread.start()
        self.backup()

    @property
    def origin(self):
        return f"http://127.0.0.1:{self.server.effective_port}"

    def stop(self):
        if self.server:
            self.server.task_dispatcher.shutdown(timeout=10)
            self.server.close()
            self.thread.join(timeout=10)
            self.server = self.thread = None
        from django.db import connections

        connections.close_all()

    def backup(self):
        return str(daily_backup(self.data_dir))


def start(data_dir, resources):
    global _runtime
    with _guard:
        if _runtime is None:
            _runtime = Runtime(data_dir, resources)
        return json.dumps({"origin": _runtime.origin, "token": _runtime.token})


def automatic_backup():
    with _guard:
        return _runtime.backup() if _runtime else ""


def export_backup(destination):
    with _guard:
        create_backup(_runtime.data_dir / "haarvinci.sqlite3", Path(destination))
        return str(destination)


def inspect_backup(source):
    metadata, _ = validate_backup(source)
    return json.dumps({"customers": metadata["tables"]["customers_customer"]})


def restore(source):
    with _guard:
        # Erst vollständig prüfen, bevor der laufende Dienst angehalten wird.
        validate_backup(source)
        _runtime.stop()
        try:
            restore_backup(source, _runtime.data_dir)
        finally:
            _runtime.start()
        return json.dumps({"origin": _runtime.origin, "token": _runtime.token})
