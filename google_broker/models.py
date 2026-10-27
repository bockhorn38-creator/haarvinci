import uuid

from django.db import models


class Handoff(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    state_hash = models.CharField(max_length=64, unique=True)
    challenge = models.CharField(max_length=128)
    device_hash = models.CharField(max_length=64)
    role = models.CharField(max_length=12)
    expires_at = models.DateTimeField()
    status = models.CharField(max_length=12, default="pending")
    encrypted_payload = models.TextField(blank=True)


class Device(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    secret_hash = models.CharField(max_length=64)
    role = models.CharField(max_length=12)
