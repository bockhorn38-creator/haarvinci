"""Lizenzhinweise der verwendeten Python-Komponenten zum Programmpaket hinzufügen."""

import importlib.metadata
import shutil
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
licenses = root / "licenses"
for name in [
    "Django",
    "django-axes",
    "whitenoise",
    "waitress",
    "asgiref",
    "sqlparse",
    "PySide6",
    "PySide6-Essentials",
    "PySide6-Addons",
    "PySide6-WebEngine",
    "shiboken6",
    "tzdata",
]:
    try:
        distribution = importlib.metadata.distribution(name)
    except importlib.metadata.PackageNotFoundError:
        continue
    for entry in distribution.files or []:
        if any(
            part.lower().startswith(("license", "copying", "copyright")) for part in entry.parts
        ):
            source = Path(distribution.locate_file(entry))
            if source.is_file():
                target = licenses / name / Path(*entry.parts[-2:])
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
for name in ["LICENSE", "LICENSE.txt"]:
    source = Path(sys.base_prefix) / name
    if source.is_file():
        shutil.copyfile(source, licenses / "Python-LICENSE.txt")
