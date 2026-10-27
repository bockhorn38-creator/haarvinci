import uuid

from django.db import migrations

NAMES = [
    "Erstberatung",
    "Haarverlängerung",
    "Haarverdichtung",
    "Extensions hochsetzen",
    "Extensions entfernen",
    "Kontrolle",
    "Sonstiger Termin",
]


def seed(apps, schema_editor):
    model = apps.get_model("appointments", "AppointmentType")
    for index, name in enumerate(NAMES):
        model.objects.get_or_create(
            id=uuid.uuid5(uuid.NAMESPACE_URL, "https://haarvinci.de/terminart/" + str(index)),
            defaults={"name": name, "order": index},
        )


class Migration(migrations.Migration):
    dependencies = [("appointments", "0001_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
