# Haarvinci Desktop – Hinweise zu verwendeten Komponenten

Haarvinci verwendet Python, Django, django-axes, WhiteNoise, Waitress und Qt for Python/PySide6 mit Qt WebEngine. Die Urheberrechte an diesen Komponenten verbleiben bei ihren jeweiligen Rechteinhabern. Weitere Komponenten und exakte Versionsstände sind in uv.lock dokumentiert.

Qt for Python/PySide6, Shiboken und die hier verwendeten Qt-Module werden unter der LGPLv3 genutzt. Sie werden als austauschbare dynamische Bibliotheken im Unterordner _internal verteilt. Das Programmpaket ist bewusst kein verschlossenes Ein-Datei-Archiv. Die LGPLv3 und GPLv3 liegen unter licenses bei. Die von der LGPL gestattete Untersuchung und das Debugging zur Verwendung geänderter Bibliotheken werden nicht eingeschränkt.

Quelltexte und Informationen der Komponenten:

- Qt for Python/PySide6 und Shiboken: https://code.qt.io/pyside/pyside-setup.git/
- Qt und Qt WebEngine einschließlich der jeweiligen Drittanbieterhinweise: https://code.qt.io/qt/qtbase.git/ und https://code.qt.io/qt/qtwebengine.git/
- Python: https://github.com/python/cpython
- Django: https://github.com/django/django
- django-axes: https://github.com/jazzband/django-axes
- WhiteNoise: https://github.com/evansd/whitenoise
- Waitress: https://github.com/Pylons/waitress

Die Build-Anleitung und der Haarvinci-Quellcode liegen im Repository bockhorn38-creator/haarvinci. Es werden keine Kopierschutzmaßnahmen oder Signaturprüfungen eingebaut, die einen Austausch LGPL-lizenzierter Bibliotheken verhindern. Die jeweilige Lizenz ist maßgeblich; diese Hinweise räumen keine zusätzlichen Rechte an fremden Komponenten ein.
