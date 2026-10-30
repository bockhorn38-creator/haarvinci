"""Kundenbezogene Vorgänge, Preis-Momentaufnahmen und nachvollziehbare Geldbuchungen."""

import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q, Sum
from django.utils import timezone

ZERO = Decimal("0.00")
MAX_MONEY = Decimal("9999999.99")


class Owned(models.QuerySet):
    def for_user(self, user):
        return self.filter(owner=user)


class PriceOption(models.Model):
    class Category(models.TextChoices):
        WEAVING = "weaving", "Weaving-Gesamtpreis nach Reihen"
        SERVICE = "service", "Zusatzleistung"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    name = models.CharField("Bezeichnung", max_length=120)
    category = models.CharField("Preisart", choices=Category.choices, max_length=12)
    rows = models.PositiveSmallIntegerField(
        "Reihen", null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(20)]
    )
    price = models.DecimalField(
        "Gesamtpreis (€)", max_digits=9, decimal_places=2, validators=[MinValueValidator(ZERO)]
    )
    active = models.BooleanField("Für neue Vorgänge verfügbar", default=True)
    version = models.PositiveIntegerField(default=1)
    objects = Owned.as_manager()

    class Meta:
        ordering = ["category", "rows", "name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "rows"],
                condition=Q(category="weaving"),
                name="treatment_one_row_tariff",
            ),
            models.CheckConstraint(condition=Q(price__gte=0), name="treatment_price_nonnegative"),
            models.CheckConstraint(
                condition=(
                    Q(category="weaving", rows__gte=1, rows__lte=20)
                    | Q(category="service", rows__isnull=True)
                ),
                name="treatment_tariff_row_shape",
            ),
        ]

    def __str__(self):
        from django.utils.formats import number_format

        return f"{self.name} · {number_format(self.price, 2)} €"


class Treatment(models.Model):
    class Status(models.TextChoices):
        PLANNED = "planned", "Geplant"
        COMPLETED = "completed", "Durchgeführt"
        CANCELLED = "cancelled", "Storniert"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    customer = models.ForeignKey(
        "customers.Customer", on_delete=models.PROTECT, related_name="treatments"
    )
    appointment = models.OneToOneField(
        "appointments.Appointment",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="treatment",
    )
    creation_key = models.UUIDField(default=uuid.uuid4, editable=False)
    creation_digest = models.CharField(max_length=64, editable=False, default="", blank=True)
    performed_on = models.DateField("Behandlungsdatum", default=timezone.localdate)
    description = models.CharField("Behandlung", max_length=200)
    status = models.CharField(
        "Status", choices=Status.choices, default=Status.PLANNED, max_length=12
    )
    rows = models.PositiveSmallIntegerField("Weaving-Reihen", null=True, blank=True)
    price_mode = models.CharField(
        max_length=12,
        choices=[("weaving", "Nach Preisliste"), ("individual", "Individueller Gesamtpreis")],
    )
    charge_extensions = models.BooleanField(default=False)
    total = models.DecimalField("Vereinbarter Gesamtpreis (€)", max_digits=9, decimal_places=2)
    notes = models.TextField("Behandlungsdokumentation", blank=True, max_length=10000)
    cancelled_reason = models.CharField("Stornogrund", blank=True, max_length=1000)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = Owned.as_manager()

    class Meta:
        ordering = ["-performed_on", "-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "creation_key"], name="treatment_creation_idempotency"
            ),
            models.CheckConstraint(condition=Q(total__gte=0), name="treatment_total_nonnegative"),
            models.CheckConstraint(
                condition=Q(rows__isnull=True) | Q(rows__gte=1, rows__lte=20),
                name="treatment_rows_valid",
            ),
        ]

    def __str__(self):
        return f"{self.description} · {self.customer} · {self.performed_on:%d.%m.%Y}"

    @property
    def net_paid(self):
        data = self.payments.filter(state="posted").aggregate(
            incoming=Sum("amount", filter=Q(kind="receipt"), default=ZERO),
            outgoing=Sum("amount", filter=Q(kind="refund"), default=ZERO),
        )
        return data["incoming"] - data["outgoing"]

    @property
    def outstanding(self):
        return max(ZERO, self.total - self.net_paid) if self.status != "cancelled" else ZERO

    @property
    def refund_due(self):
        return self.net_paid if self.status == "cancelled" else ZERO


class PriceLine(models.Model):
    treatment = models.ForeignKey(Treatment, on_delete=models.CASCADE, related_name="lines")
    source = models.ForeignKey(PriceOption, on_delete=models.SET_NULL, null=True, blank=True)
    label = models.CharField(max_length=300)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]


class TreatmentExtension(models.Model):
    treatment = models.ForeignKey(
        Treatment, on_delete=models.CASCADE, related_name="extension_links"
    )
    position = models.ForeignKey(
        "extensions.ExtensionPosition", on_delete=models.SET_NULL, null=True, blank=True
    )
    position_uuid = models.UUIDField()
    label = models.CharField(max_length=400)
    snapshot = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["treatment", "position_uuid"], name="treatment_unique_extension"
            )
        ]


class Payment(models.Model):
    class Kind(models.TextChoices):
        RECEIPT = "receipt", "Zahlungseingang"
        REFUND = "refund", "Rückerstattung"

    class Purpose(models.TextChoices):
        DEPOSIT = "deposit", "Anzahlung"
        PARTIAL = "partial", "Teilzahlung"
        FINAL = "final", "Restzahlung / vollständige Zahlung"
        REFUND = "refund", "Rückerstattung"

    class Method(models.TextChoices):
        CASH = "cash", "Bar"
        BANK = "bank", "Überweisung"
        CARD = "card", "Karte"
        OTHER = "other", "Sonstige"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    treatment = models.ForeignKey(Treatment, on_delete=models.PROTECT, related_name="payments")
    booking_key = models.UUIDField(default=uuid.uuid4)
    kind = models.CharField(max_length=12, choices=Kind.choices)
    purpose = models.CharField("Buchungsart", max_length=12, choices=Purpose.choices)
    amount = models.DecimalField(
        "Betrag (€)",
        max_digits=9,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    booked_on = models.DateField("Zahlungsdatum", default=timezone.localdate)
    method = models.CharField("Zahlungsweg", max_length=12, choices=Method.choices)
    original = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="refunds"
    )
    notes = models.TextField("Notiz / Erstattungsgrund", blank=True, max_length=2000)
    state = models.CharField(
        max_length=12,
        choices=[("posted", "Gebucht"), ("voided", "Buchung storniert")],
        default="posted",
    )
    void_reason = models.CharField(max_length=1000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    objects = Owned.as_manager()

    class Meta:
        ordering = ["-booked_on", "-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "booking_key"], name="treatment_payment_idempotency"
            ),
            models.CheckConstraint(condition=Q(amount__gt=0), name="treatment_payment_positive"),
            models.CheckConstraint(
                condition=Q(kind="receipt", original__isnull=True)
                | Q(kind="refund", original__isnull=False),
                name="treatment_refund_original",
            ),
        ]

    @property
    def refundable(self):
        if self.kind != "receipt" or self.state != "posted":
            return ZERO
        return (
            self.amount
            - self.refunds.filter(state="posted").aggregate(value=Sum("amount", default=ZERO))[
                "value"
            ]
        )

    def __str__(self):
        from django.utils.formats import number_format

        return f"{self.get_purpose_display()} · {number_format(self.amount, 2)} € · {self.booked_on:%d.%m.%Y} · {self.pk.hex[:8]}"
