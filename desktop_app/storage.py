"""Lokale Konfiguration und überprüfbare, konsistente Ein-Datei-Sicherungen."""

import hashlib
import json
import os
import secrets
import sqlite3
import tempfile
import zipfile
from contextlib import closing
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from . import __version__


class BackupError(Exception):
    pass


def installation_secret(data_dir):
    data_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = data_dir / "installation.json"
    if not path.exists():
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump({"secret_key": secrets.token_urlsafe(64)}, stream)
    secret = json.loads(path.read_text(encoding="utf-8"))["secret_key"]
    if not isinstance(secret, str) or len(secret) < 50:
        raise ValueError("Die lokale Konfiguration ist beschädigt; sie wurde nicht überschrieben.")
    return secret


def _inspect(database):
    with closing(sqlite3.connect(database)) as db:
        if db.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
            raise BackupError("Die Datenbankprüfung ist fehlgeschlagen.")
        if db.execute("PRAGMA foreign_key_check").fetchall():
            raise BackupError("Die Datenbank enthält fehlerhafte Verknüpfungen.")
        tables = [
            row[0]
            for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        ]
        if not {"auth_user", "customers_customer", "django_migrations"}.issubset(tables):
            raise BackupError("Die Datei ist keine vollständige Haarvinci-Datenbank.")
        counts = {}
        for table in tables:
            quoted = '"' + table.replace('"', '""') + '"'
            counts[table] = db.execute(f"SELECT count(*) FROM {quoted}").fetchone()[0]
        return counts


def create_backup(database, destination):
    destination = Path(destination)
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as temp:
        snapshot = Path(temp) / "datenbank.sqlite3"
        with (
            closing(sqlite3.connect(database)) as source,
            closing(sqlite3.connect(snapshot)) as target,
        ):
            source.backup(target)
        counts = _inspect(snapshot)
        content = snapshot.read_bytes()
        metadata = {
            "format_version": 1,
            "app_version": __version__,
            "created_at": datetime.now(ZoneInfo("Europe/Berlin")).isoformat(),
            "sha256": hashlib.sha256(content).hexdigest(),
            "tables": counts,
        }
        archive = Path(temp) / "sicherung.haarvinci"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            bundle.writestr("manifest.json", json.dumps(metadata, ensure_ascii=False))
            bundle.write(snapshot, "datenbank.sqlite3")
        archive.chmod(0o600)
        validate_backup(archive)
        os.replace(archive, destination)
    return destination


def validate_backup(archive):
    try:
        with zipfile.ZipFile(archive) as bundle:
            if sorted(bundle.namelist()) != ["datenbank.sqlite3", "manifest.json"]:
                raise BackupError("Die Sicherung hat einen ungültigen Inhalt.")
            if (
                bundle.getinfo("datenbank.sqlite3").file_size > 1024**3
                or bundle.getinfo("manifest.json").file_size > 1024**2
            ):
                raise BackupError("Diese Sicherung überschreitet die unterstützte Größe.")
            metadata = json.loads(bundle.read("manifest.json"))
            content = bundle.read("datenbank.sqlite3")
        if metadata.get("format_version") != 1:
            raise BackupError("Diese Sicherungsversion wird nicht unterstützt.")
        if not secrets.compare_digest(
            hashlib.sha256(content).hexdigest(), metadata.get("sha256", "")
        ):
            raise BackupError("Die Sicherung ist beschädigt: Die Prüfsumme stimmt nicht.")
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "check.sqlite3"
            path.write_bytes(content)
            if _inspect(path) != metadata.get("tables"):
                raise BackupError("Die Datensatzanzahlen der Sicherung stimmen nicht überein.")
        return metadata, content
    except (OSError, ValueError, KeyError, sqlite3.DatabaseError, zipfile.BadZipFile) as error:
        raise BackupError(
            "Die Datei konnte nicht als Haarvinci-Sicherung gelesen werden."
        ) from error


def daily_backup(data_dir):
    directory = data_dir / "Sicherungen"
    day = datetime.now(ZoneInfo("Europe/Berlin")).strftime("%Y-%m-%d")
    path = directory / f"Haarvinci-{day}.haarvinci"
    if path.exists():
        try:
            validate_backup(path)
            if path.stat().st_mtime_ns >= (data_dir / "haarvinci.sqlite3").stat().st_mtime_ns:
                return path
        except BackupError:
            pass
    return create_backup(data_dir / "haarvinci.sqlite3", path)


def restore_backup(archive, data_dir):
    """Nur vor Serverstart und unter der Instanzsperre aufrufen."""
    _, content = validate_backup(archive)
    database = data_dir / "haarvinci.sqlite3"
    if database.exists():
        stamp = datetime.now(ZoneInfo("Europe/Berlin")).strftime("%Y-%m-%d-%H%M%S")
        create_backup(
            database,
            data_dir
            / "Sicherungen"
            / f"Vor-Wiederherstellung-{stamp}-{secrets.token_hex(3)}.haarvinci",
        )
    data_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=data_dir, delete=False) as stream:
        pending = Path(stream.name)
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        # Keine geöffnete Verbindung: alter Stand bleibt bis zum atomaren Tausch gültig.
        # Eventuelle Crash-Journale werden vorher durch SQLite konsistent abgeschlossen.
        if database.exists():
            with closing(sqlite3.connect(database)) as db:
                db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        os.replace(pending, database)
    finally:
        pending.unlink(missing_ok=True)
