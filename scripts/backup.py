#!/usr/bin/env python3
"""Lokale PostgreSQL-Sicherungen; keine Geheimnisse in Argumenten oder Ausgaben."""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.umask(0o077)
import django  # noqa: E402

django.setup()
from django.db import DatabaseError, connection, transaction  # noqa: E402

BACKUPS = ROOT / ".local" / "backups"


class BackupError(Exception):
    pass


def docker(command, *, stdin=None, stdout=subprocess.PIPE):
    return subprocess.run(
        ["docker", "compose", "exec", "-T", "db", "sh", "-c", command[0], "sh", *command[1:]],
        cwd=ROOT,
        stdin=stdin,
        stdout=stdout,
        stderr=subprocess.PIPE,
        check=True,
    )


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify(path):
    metadata = json.loads(path.with_suffix(".json").read_text())
    if metadata.get("sha256") != digest(path):
        raise BackupError("Die Prüfsumme stimmt nicht. Sicherung nicht verwenden.")
    with path.open("rb") as stream:
        docker(["exec pg_restore --list"], stdin=stream)
    if not metadata.get("tables") or any(
        not re.fullmatch(r"[a-z_][a-z0-9_]*", table) for table in metadata["tables"]
    ):
        raise BackupError("Ungültiges Sicherungsmanifest.")
    return metadata


def backup(daily=False):
    BACKUPS.mkdir(mode=0o700, parents=True, exist_ok=True)
    if daily:
        for previous in sorted(
            BACKUPS.glob(f"haarvinci-{datetime.now(UTC):%Y%m%d}-*.dump"), reverse=True
        ):
            try:
                verify(previous)
                print("Die heutige Sicherung ist bereits vorhanden und geprüft.")
                return previous
            except (BackupError, ValueError, OSError, subprocess.CalledProcessError):
                continue
    path = BACKUPS / f"haarvinci-{datetime.now(UTC):%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}.dump"
    try:
        # pg_dump und Zählung sehen durch denselben Snapshot exakt denselben Datenstand.
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
                cursor.execute("SELECT pg_export_snapshot()")
                snapshot = cursor.fetchone()[0]
                tables = connection.introspection.table_names(cursor)
                counts = {}
                for table in tables:
                    cursor.execute(f"SELECT count(*) FROM {connection.ops.quote_name(table)}")
                    counts[table] = cursor.fetchone()[0]
            with path.open("xb") as stream:
                docker(
                    [
                        'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc --no-owner --no-acl --snapshot="$1"',
                        snapshot,
                    ],
                    stdout=stream,
                )
                stream.flush()
                os.fsync(stream.fileno())
        metadata = {
            "format_version": 1,
            "created_at": datetime.now(UTC).isoformat(),
            "sha256": digest(path),
            "tables": counts,
        }
        with path.with_suffix(".json").open("x") as stream:
            json.dump(metadata, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        verify(path)
    except BaseException:
        path.unlink(missing_ok=True)
        path.with_suffix(".json").unlink(missing_ok=True)
        raise
    print(f"Sicherung erstellt und geprüft: {path.relative_to(ROOT)}")
    return path


def restore(path, database, *, temporary=False):
    metadata = verify(path)
    if not re.fullmatch(r"haarvinci_[a-z0-9_]{1,45}", database):
        raise BackupError(
            "Zieldatenbank muss mit haarvinci_ beginnen und Kleinbuchstaben/Ziffern enthalten."
        )
    docker(['exec createdb -U "$POSTGRES_USER" -T template0 "$1"', database])
    try:
        with path.open("rb") as stream:
            docker(
                [
                    'exec pg_restore -U "$POSTGRES_USER" --no-owner --no-acl --exit-on-error -d "$1"',
                    database,
                ],
                stdin=stream,
            )
        items = ", ".join(
            f"'{table}', (SELECT count(*) FROM public.\"{table}\")" for table in metadata["tables"]
        )
        query = f"SELECT json_build_object({items})"
        result = docker(
            [
                'exec psql -U "$POSTGRES_USER" -d "$1" -At -v ON_ERROR_STOP=1 -c "$2"',
                database,
                query,
            ]
        )
        if json.loads(result.stdout) != metadata["tables"]:
            raise BackupError("Die wiederhergestellten Datensatzanzahlen weichen ab.")
        print("Wiederherstellung erfolgreich: alle Tabellen und Datensatzanzahlen stimmen überein.")
        if not temporary:
            print(
                f"Die wiederhergestellte Datenbank heißt {database}. Die aktuelle Datenbank blieb unverändert."
            )
    finally:
        if temporary:
            docker(['exec dropdb -U "$POSTGRES_USER" "$1"', database])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    create = sub.add_parser("backup")
    create.add_argument("--daily", action="store_true")
    for action in ["verify", "restore-test", "restore"]:
        command = sub.add_parser(action)
        command.add_argument("archive", type=Path)
        if action == "restore":
            command.add_argument("--database", required=True)
    args = parser.parse_args()
    if os.getenv("DATABASE_URL") or os.getenv("POSTGRES_HOST", "127.0.0.1") not in {
        "127.0.0.1",
        "localhost",
    }:
        raise BackupError(
            "Dieses Werkzeug ist für die lokale Compose-Datenbank. Externe Datenbanken mit den Sicherungswerkzeugen des Anbieters sichern."
        )
    if args.action == "backup":
        backup(args.daily)
    elif args.action == "verify":
        verify(args.archive)
        print("Prüfsumme und PostgreSQL-Archiv sind gültig.")
    else:
        temporary = args.action == "restore-test"
        name = f"haarvinci_restore_{uuid.uuid4().hex[:12]}" if temporary else args.database
        restore(args.archive, name, temporary=temporary)


if __name__ == "__main__":
    try:
        main()
    except BackupError as error:
        print(f"Sicherungsvorgang fehlgeschlagen: {error}", file=sys.stderr)
        sys.exit(1)
    except (DatabaseError, ValueError, OSError, subprocess.CalledProcessError) as error:
        # stderr von Datenbankwerkzeugen kann Details enthalten; keine Verbindungswerte ausgeben.
        print(
            f"Sicherungsvorgang fehlgeschlagen ({type(error).__name__}). Keine bestehende Datenbank wurde gelöscht.",
            file=sys.stderr,
        )
        sys.exit(1)
