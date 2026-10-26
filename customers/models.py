import unicodedata
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class CustomerQuerySet(models.QuerySet):
    def for_user(self, user):
        return self.filter(owner=user)


class Customer(models.Model):
    """Stabile UUID als Bezugspunkt für spätere, getrennte Fachmodule."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="customers"
    )
    first_name = models.CharField("Vorname", max_length=80)
    last_name = models.CharField("Nachname", max_length=100)
    phone = models.CharField("Telefonnummer", max_length=40, blank=True)
    phone_digits = models.CharField(max_length=40, blank=True, editable=False)
    search_text = models.TextField(blank=True, editable=False)
    email = models.EmailField("E-Mail-Adresse", blank=True)
    street = models.CharField("Straße und Hausnummer", max_length=160, blank=True)
    postal_code = models.CharField("Postleitzahl", max_length=12, blank=True)
    city = models.CharField("Ort", max_length=100, blank=True)
    birthday = models.DateField("Geburtsdatum", null=True, blank=True)
    first_consultation = models.DateField(
        "Erste Beratung", null=True, blank=True, default=timezone.localdate
    )
    notes = models.TextField("Persönliche Notizen", blank=True, max_length=10000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.PositiveIntegerField(default=1)
    objects = CustomerQuerySet.as_manager()

    class Meta:
        ordering = ["last_name", "first_name", "id"]
        indexes = [models.Index(fields=["owner", "last_name", "first_name"])]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def initials(self):
        return f"{self.first_name[:1]}{self.last_name[:1]}".upper()

    @property
    def tone(self):
        return ["rose", "sage", "sand", "lilac"][sum(map(ord, str(self))) % 4]

    def save(self, *args, **kwargs):
        self.phone_digits = "".join(c for c in self.phone if c.isdigit())
        self.search_text = unicodedata.normalize(
            "NFKC",
            "\n".join([self.first_name, self.last_name, self.phone, self.phone_digits, self.email]),
        ).casefold()
        super().save(*args, **kwargs)
