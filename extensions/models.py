import unicodedata
import uuid
from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class PositionQuerySet(models.QuerySet):
    def for_user(self, user):
        return self.filter(customer__owner=user)


class ExtensionPosition(models.Model):
    """Eine kundenbezogene Position. Preise sind Gesamtpreise, keine Lagerbuchung."""

    class Delivery(models.TextChoices):
        PLANNED = "planned", "Geplant"
        ORDERED = "ordered", "Bestellt"
        RECEIVED = "received", "Geliefert"
        CANCELLED = "cancelled", "Storniert"

    class Unit(models.TextChoices):
        STRANDS = "strands", "Strähnen"
        PACKS = "packs", "Packungen"
        PIECES = "pieces", "Stück"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(
        "customers.Customer", on_delete=models.CASCADE, related_name="extensions"
    )
    manufacturer = models.CharField("Hersteller", max_length=120)
    extension_type = models.CharField("Extensions-Art", max_length=100)
    color = models.CharField("Haarfarbe", max_length=120)
    color_code = models.CharField("Hersteller-Farbcode", max_length=80, blank=True)
    length_cm = models.DecimalField(
        "Haarlänge (cm)",
        max_digits=5,
        decimal_places=1,
        validators=[MinValueValidator(Decimal("0.1")), MaxValueValidator(300)],
    )
    weight_g = models.DecimalField(
        "Gesamtgewicht (g)",
        max_digits=7,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01")), MaxValueValidator(10000)],
    )
    quantity = models.PositiveIntegerField(
        "Anzahl",
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(100000)],
    )
    quantity_unit = models.CharField(
        "Einheit der Anzahl", choices=Unit.choices, max_length=12, blank=True
    )
    purchase_price = models.DecimalField(
        "Einkaufspreis gesamt (€)",
        max_digits=9,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    sale_price = models.DecimalField(
        "Verkaufspreis gesamt (€)",
        max_digits=9,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    assigned_on = models.DateField("Bestell- / Zuordnungsdatum", default=timezone.localdate)
    delivery_status = models.CharField(
        "Lieferstatus", max_length=12, choices=Delivery.choices, blank=True
    )
    notes = models.TextField("Zusätzliche Notizen", max_length=4000, blank=True)
    version = models.PositiveIntegerField(default=1)
    search_text = models.TextField(blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = PositionQuerySet.as_manager()

    class Meta:
        ordering = ["-assigned_on", "-created_at", "-id"]
        indexes = [models.Index(fields=["customer", "-assigned_on"])]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(length_cm__gt=0) & models.Q(length_cm__lte=300),
                name="extensions_length_range",
            ),
            models.CheckConstraint(
                condition=models.Q(weight_g__gt=0) & models.Q(weight_g__lte=10000),
                name="extensions_weight_range",
            ),
            models.CheckConstraint(
                condition=models.Q(purchase_price__gte=0), name="extensions_purchase_nonnegative"
            ),
            models.CheckConstraint(
                condition=models.Q(sale_price__isnull=True) | models.Q(sale_price__gte=0),
                name="extensions_sale_nonnegative",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(quantity__isnull=True, quantity_unit="")
                    | (
                        models.Q(quantity__isnull=False, quantity__gte=1, quantity__lte=100000)
                        & models.Q(quantity_unit__in=["strands", "packs", "pieces"])
                    )
                ),
                name="extensions_quantity_pair",
            ),
        ]

    def __str__(self):
        return f"{self.manufacturer} · {self.extension_type} · {self.color}"

    def save(self, *args, **kwargs):
        self.search_text = unicodedata.normalize(
            "NFKC", "\n".join([self.manufacturer, self.extension_type, self.color, self.color_code])
        ).casefold()
        super().save(*args, **kwargs)
