import uuid

from django.conf import settings
from django.db import models


class ImportReceipt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    import_id = models.UUIDField()
    source_digest = models.CharField(max_length=64)
    plan_digest = models.CharField(max_length=64)
    counts = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["owner", "import_id"], name="intake_unique_import_id"),
            models.UniqueConstraint(fields=["owner", "plan_digest"], name="intake_unique_plan"),
        ]
