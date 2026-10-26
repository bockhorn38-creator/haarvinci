#!/usr/bin/env python3
"""Lokaler Webserver mit regelmäßiger Sicherung und gemeinsamem sauberem Beenden."""

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backup-interval", type=int, default=3600)
    args = parser.parse_args()
    if args.backup_interval < 1:
        parser.error("Das Sicherungsintervall muss positiv sein.")
    command = [
        str(ROOT / ".venv/bin/gunicorn"),
        "config.wsgi:application",
        "--bind",
        f"127.0.0.1:{os.getenv('HAARVINCI_PORT', '8000')}",
        "--workers",
        "2",
        "--no-control-socket",
        "--access-logfile",
        "-",
        "--access-logformat",
        "%(t)s %(m)s %(U)s %(s)s %(L)s",
        "--error-logfile",
        "-",
    ]
    server = subprocess.Popen(command, cwd=ROOT)
    stopping = False

    def stop(signum, frame):
        nonlocal stopping
        stopping = True
        if server.poll() is None:
            server.terminate()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    due = time.monotonic() + args.backup_interval
    try:
        while server.poll() is None:
            try:
                server.wait(timeout=max(0.1, min(30, due - time.monotonic())))
            except subprocess.TimeoutExpired:
                if stopping or time.monotonic() < due:
                    continue
                try:
                    result = subprocess.run(
                        [sys.executable, "scripts/backup.py", "backup", "--daily"],
                        cwd=ROOT,
                        timeout=180,
                        check=False,
                    )
                    success = result.returncode == 0
                except subprocess.TimeoutExpired:
                    success = False
                if not success:
                    print(
                        "WARNUNG: Regelmäßige Sicherung fehlgeschlagen. Erneuter Versuch in fünf Minuten; bitte Protokoll prüfen.",
                        file=sys.stderr,
                        flush=True,
                    )
                due = time.monotonic() + (args.backup_interval if success else 300)
        return 0 if stopping else server.returncode
    finally:
        if server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=30)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()


if __name__ == "__main__":
    sys.exit(main())
