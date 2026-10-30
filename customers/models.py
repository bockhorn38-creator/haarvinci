import unicodedata
import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
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
    natural_color = models.CharField("Naturhaarfarbe", max_length=120, blank=True)
    current_color = models.CharField("Aktuelle Haarfarbe", max_length=120, blank=True)
    hair_structure = models.CharField("Haarstruktur", max_length=120, blank=True)
    natural_length = models.DecimalField(
        "Eigenhaarlänge (cm)",
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(300)],
    )
    desired_length = models.DecimalField(
        "Gewünschte Haarlänge (cm)",
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(300)],
    )
    hair_density = models.CharField("Haarstärke / Haardichte", max_length=160, blank=True)
    current_extensions = models.TextField(
        "Aktuell getragene Extensions", max_length=2000, blank=True
    )
    hair_wishes = models.TextField("Besonderheiten und Wünsche", max_length=4000, blank=True)
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


class CustomerEvent(models.Model):
    """Unveränderliche Momentaufnahme; UUID-Referenz bleibt nach Positionslöschung erhalten."""

    class Kind(models.TextChoices):
        TREATMENT_CREATED = "treatment_created", "Behandlung angelegt"
        TREATMENT_UPDATED = "treatment_updated", "Behandlung aktualisiert"
        TREATMENT_CANCELLED = "treatment_cancelled", "Behandlung storniert"
        PAYMENT_RECEIVED = "payment_received", "Zahlung dokumentiert"
        PAYMENT_REFUNDED = "payment_refunded", "Rückerstattung dokumentiert"
        PAYMENT_VOIDED = "payment_voided", "Buchung storniert"
        APPOINTMENT_CREATED = "appointment_created", "Termin vereinbart"
        APPOINTMENT_UPDATED = "appointment_updated", "Termin geändert"
        APPOINTMENT_CANCELLED = "appointment_cancelled", "Termin abgesagt"
        CREATED = "created", "Kundenakte angelegt"
        PROFILE = "profile", "Kundenakte aktualisiert"
        EXTENSION_CREATED = "extension_created", "Extensions zugeordnet"
        EXTENSION_UPDATED = "extension_updated", "Extensions geändert"
        EXTENSION_DELETED = "extension_deleted", "Extensions gelöscht"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    kind = models.CharField(max_length=24, choices=Kind.choices)
    occurred_on = models.DateField("Datum")
    recorded_at = models.DateTimeField(auto_now_add=True)
    treatment_uuid = models.UUIDField(null=True, editable=False)
    extension_uuid = models.UUIDField(null=True, editable=False)
    appointment_uuid = models.UUIDField(null=True, editable=False)
    summary = models.CharField(max_length=500)
    snapshot = models.JSONField(default=dict)
    changes = models.JSONField(default=list)

    class Meta:
        ordering = ["-occurred_on", "-recorded_at", "-id"]
        indexes = [models.Index(fields=["customer", "-occurred_on", "-recorded_at"])]

    @property
    def snapshot_rows(self):
        if self.treatment_uuid:
            return [
                {"label": str(key), "value": str(value)} for key, value in self.snapshot.items()
            ]
        if not self.extension_uuid:
            return []
        from django.apps import apps

        from .history import display_value

        model = apps.get_model("extensions", "ExtensionPosition")
        return [
            {
                "label": str(model._meta.get_field(name).verbose_name),
                "value": display_value(model._meta.get_field(name), value),
            }
            for name, value in self.snapshot.items()
        ]
