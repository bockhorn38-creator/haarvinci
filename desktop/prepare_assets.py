"""Windows-Symbol ohne zusätzliche Bildbibliothek aus dem vorhandenen PNG erzeugen."""

import struct
from pathlib import Path

root = Path(__file__).resolve().parent.parent
image = (root / "static/img/icon-192.png").read_bytes()
header = struct.pack("<HHH", 0, 1, 1)
entry = struct.pack("<BBBBHHII", 192, 192, 0, 0, 1, 32, len(image), 22)
(root / "desktop/assets/haarvinci.ico").write_bytes(header + entry + image)
