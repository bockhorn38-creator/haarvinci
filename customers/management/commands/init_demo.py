import os
import secrets
from datetime import date
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from customers.models import Customer

DEMO = [
    (
        "Marie",
        "Sommer",
        "+49 151 0000 0101",
        "marie.sommer@example.com",
        "2026-09-04",
        "Wünscht sich mehr Fülle und einen natürlichen Übergang. Bevorzugt Termine am Vormittag.",
    ),
    (
        "Lena",
        "Bergmann",
        "+49 151 0000 0102",
        "lena.bergmann@example.com",
        "2026-09-12",
        "Mag warme, natürliche Blondtöne. Beim nächsten Gespräch mögliche Längen besprechen.",
    ),
    (
        "Sophie",
        "Winter",
        "+49 151 0000 0103",
        "sophie.winter@example.com",
        "2026-10-02",
        "Möchte sich zunächst über Haarverdichtung informieren. Nimmt sich gern Zeit für die Beratung.",
    ),
    (
        "Amira",
        "Blum",
        "+49 151 0000 0104",
        "amira.blum@example.com",
        "2026-10-08",
        "Wünscht sich einen unkomplizierten Look für den Alltag. Sanfte Pflege ist ihr besonders wichtig.",
    ),
    ("Julia", "Linden", "+49 151 0000 0105", "julia.linden@example.com", "2026-10-14", ""),
    (
        "Nora",
        "Feld",
        "+49 151 0000 0106",
        "nora.feld@example.com",
        "2026-10-20",
        "Hat erste Ideen für einen längeren Look. Gemeinsam passende Farbtöne ansehen.",
    ),
]


class Command(BaseCommand):
    help = "Legt einmalig einen lokalen Demo-Zugang und ausschließlich fiktive Kundinnen an."

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Testdaten und Demo-Zugang sind nur bei DJANGO_DEBUG=true erlaubt.")
        User = get_user_model()
        existing = User.objects.filter(username="conny").first()
        if existing:
            self.stdout.write(
                "Zugang besteht bereits. Kein Passwort und keine Kundendaten verändert."
            )
            return
        if User.objects.exists():
            raise CommandError(
                "Es gibt bereits Benutzer. Demo-Daten werden nicht automatisch ergänzt."
            )
        password = secrets.token_urlsafe(20)
        user = User.objects.create_user(username="conny", first_name="Conny", password=password)
        for first, last, phone, email, consultation, notes in DEMO:
            Customer.objects.create(
                owner=user,
                first_name=first,
                last_name=last,
                phone=phone,
                email=email,
                first_consultation=date.fromisoformat(consultation),
                notes=notes,
            )
        path = Path(settings.BASE_DIR) / ".local" / "demo-access.txt"
        path.parent.mkdir(mode=0o700, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as stream:
            stream.write(f"Benutzername: conny\nPasswort: {password}\n")
        self.stdout.write(
            "6 fiktive Kundinnen angelegt. Lokaler Zugang: .local/demo-access.txt (nicht in Git)."
        )
