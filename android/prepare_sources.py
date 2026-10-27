"""Nur bekannte, generierte Android-Unterordner aktualisieren; keine Benutzerdaten."""

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ANDROID = ROOT / "android/app/src/main"
PYTHON = ANDROID / "python"
for package in ["config", "core", "customers", "extensions", "appointments"]:
    destination = PYTHON / package
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(
        ROOT / package, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
    )
destination = PYTHON / "desktop_app"
destination.mkdir(exist_ok=True)
for name in ["__init__.py", "storage.py", "urls.py", "views.py"]:
    shutil.copyfile(ROOT / "desktop_app" / name, destination / name)
assets = ANDROID / "assets/haarvinci"
if assets.exists():
    shutil.rmtree(assets)
assets.mkdir(parents=True)
for directory in ["templates", "static"]:
    shutil.copytree(ROOT / directory, assets / directory)
print("Gemeinsamer Anwendungskern und Android-Ressourcen vorbereitet.")
