# PyInstaller: echter Windows-Build auf Windows, Linux-Build als zusätzliche Prüfung.
import os
import secrets
import sys
import tempfile
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

root = Path(SPECPATH).parent
sys.path.insert(0, str(root))
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.desktop_settings'
os.environ['HAARVINCI_DATA_DIR'] = tempfile.mkdtemp(prefix='haarvinci-build-')
os.environ['HAARVINCI_DESKTOP_SECRET'] = secrets.token_urlsafe(64)
os.environ['HAARVINCI_DESKTOP_TOKEN'] = secrets.token_urlsafe(48)

hidden = []
for package in ['config', 'core', 'customers', 'extensions', 'desktop_app', 'axes', 'whitenoise']:
    hidden += collect_submodules(package)
data = [(str(root / 'templates'), 'templates'),
        (str(root / 'static'), 'static'),
        (str(root / 'desktop/licenses'), 'licenses'),
        (str(root / 'desktop/THIRD_PARTY_NOTICES.md'), '.')]
# Eigene Migrationen bleiben auch im eingefrorenen Programmpaket importierbar.
data += collect_data_files('customers', include_py_files=True, includes=['migrations/*.py'])
data += collect_data_files('extensions', include_py_files=True, includes=['migrations/*.py'])
data += collect_data_files('axes', include_py_files=True, includes=['migrations/*.py'])

a = Analysis([str(root / 'desktop/run.py')], pathex=[str(root)], binaries=[], datas=data,
             hiddenimports=hidden, hookspath=[], runtime_hooks=[],
             excludes=['playwright', 'ruff', 'gunicorn', 'psycopg', 'psycopg_binary', 'django.db.backends.postgresql', 'django.db.backends.mysql', 'django.contrib.gis', 'tests'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='Haarvinci',
          debug=False, strip=False, upx=False, console=False,
          icon=str(root / 'desktop/assets/haarvinci.ico') if os.name == 'nt' else None)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='Haarvinci')
