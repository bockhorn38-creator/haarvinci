import uuid

from django.db import migrations, models


def assign_keys(apps, schema_editor):
    treatment = apps.get_model("treatments", "Treatment")
    for key in (
        treatment.objects.using(schema_editor.connection.alias)
        .values_list("pk", flat=True)
        .iterator()
    ):
        treatment.objects.using(schema_editor.connection.alias).filter(pk=key).update(
            creation_key=uuid.uuid4()
        )


class Migration(migrations.Migration):
    dependencies = [("treatments", "0002_alter_priceline_amount")]
    operations = [
        migrations.AddField(
            model_name="treatment",
            name="creation_key",
            field=models.UUIDField(null=True, editable=False),
        ),
        migrations.AddField(
            model_name="treatment",
            name="creation_digest",
            field=models.CharField(max_length=64, editable=False, default="", blank=True),
        ),
        migrations.RunPython(assign_keys, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="treatment",
            name="creation_key",
            field=models.UUIDField(default=uuid.uuid4, editable=False),
        ),
        migrations.AddConstraint(
            model_name="treatment",
            constraint=models.UniqueConstraint(
                fields=("owner", "creation_key"), name="treatment_creation_idempotency"
            ),
        ),
    ]
