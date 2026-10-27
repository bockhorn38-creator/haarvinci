"""Android nutzt dieselben festgelegten Python-Pakete und Prüfsummen wie uv.lock."""

import tomllib
from pathlib import Path

root = Path(__file__).resolve().parent.parent
packages = tomllib.loads((root / "uv.lock").read_text())["package"]
names = {"django", "asgiref", "sqlparse", "django-axes", "whitenoise", "waitress", "tzdata"}
lines = ["# Aus uv.lock erzeugt; nur plattformunabhängige Pakete."]
for package in packages:
    if package["name"] not in names:
        continue
    wheels = [
        wheel for wheel in package.get("wheels", []) if wheel["url"].endswith("-none-any.whl")
    ]
    if not wheels:
        raise ValueError(f"Kein plattformunabhängiges Paket für {package['name']}")
    hashes = " ".join("--hash=" + wheel["hash"] for wheel in wheels)
    lines.append(f"{package['name']}=={package['version']} {hashes}")
    names.remove(package["name"])
if names:
    raise ValueError(f"Fehlende Abhängigkeiten: {sorted(names)}")
(root / "android/requirements.lock").write_text("\n".join(lines) + "\n")
