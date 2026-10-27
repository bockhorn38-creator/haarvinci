import uuid
from datetime import UTC, timedelta

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class OwnedQuerySet(models.QuerySet):
    def for_user(self, user):
        return self.filter(owner=user)


class AppointmentType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True)
    name = models.CharField("Terminart", max_length=100)
    order = models.PositiveSmallIntegerField(default=100)

    class Meta:
        ordering = ["order", "name", "id"]

    def __str__(self):
        return self.name


class CalendarSettings(models.Model):
    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    instance_id = models.UUIDField(default=uuid.uuid4, editable=False)
    broker_url = models.URLField("Adresse des Google-Anmeldedienstes", blank=True, max_length=500)


class CalendarConnection(models.Model):
    class Role(models.TextChoices):
        BUSINESS = "business", "Geschäftlich"
        PRIVATE = "private", "Privat"

    class State(models.TextChoices):
        DISCONNECTED = "disconnected", "Nicht verbunden"
        PENDING = "pending", "Anmeldung läuft"
        CHOOSE = "choose", "Kalender auswählen"
        CONNECTED = "connected", "Verbunden"
        ERROR = "error", "Synchronisierung ausstehend"
        AUTH = "auth", "Erneute Anmeldung erforderlich"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=12, choices=Role.choices)
    calendar_id = models.CharField(max_length=1024, blank=True)
    state = models.CharField(max_length=16, choices=State.choices, default=State.DISCONNECTED)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    window_start = models.DateTimeField(null=True, blank=True)
    window_end = models.DateTimeField(null=True, blank=True)
    error_code = models.CharField(max_length=24, blank=True)
    objects = OwnedQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "role"], name="calendar_one_connection_per_role"
            )
        ]
        ordering = ["role"]


class Appointment(models.Model):
    class Status(models.TextChoices):
        PLANNED = "planned", "Geplant"
        CONFIRMED = "confirmed", "Bestätigt"
        COMPLETED = "completed", "Abgeschlossen"
        CANCELLED = "cancelled", "Abgesagt"

    class Sync(models.TextChoices):
        LOCAL = "local", "Nur lokal"
        PENDING = "pending", "Übertragung ausstehend"
        SYNCED = "synced", "Synchronisiert"
        CONFLICT = "conflict", "Synchronisierungskonflikt"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    customer = models.ForeignKey(
        "customers.Customer", on_delete=models.PROTECT, related_name="appointments"
    )
    appointment_type = models.ForeignKey(AppointmentType, on_delete=models.PROTECT)
    start_at = models.DateTimeField("Beginn")
    end_at = models.DateTimeField("Ende")
    buffer_minutes = models.PositiveSmallIntegerField(
        "Puffer danach (Minuten)",
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(240)],
    )
    notes = models.TextField("Zusätzliche Notizen", max_length=4000, blank=True)
    status = models.CharField(
        "Terminstatus", choices=Status.choices, max_length=12, default=Status.PLANNED
    )
    version = models.PositiveIntegerField(default=1)
    google_event_id = models.CharField(max_length=256, blank=True)
    google_calendar_id = models.CharField(max_length=1024, blank=True)
    google_etag = models.CharField(max_length=256, blank=True)
    google_generation = models.PositiveIntegerField(default=0)
    google_title = models.CharField(max_length=300, blank=True)
    google_baseline = models.JSONField(default=dict)
    sync_state = models.CharField(max_length=12, choices=Sync.choices, default=Sync.LOCAL)
    last_synced_version = models.PositiveIntegerField(default=0)
    remote_conflict = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = OwnedQuerySet.as_manager()

    class Meta:
        ordering = ["start_at", "id"]
        indexes = [
            models.Index(fields=["owner", "start_at"]),
            models.Index(fields=["customer", "-end_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_at__gt=models.F("start_at")),
                name="appointment_positive_duration",
            ),
            models.CheckConstraint(
                condition=models.Q(buffer_minutes__lte=240), name="appointment_buffer_limit"
            ),
        ]

    @property
    def duration_minutes(self):
        return int(
            (self.end_at.astimezone(UTC) - self.start_at.astimezone(UTC)).total_seconds() // 60
        )

    @property
    def busy_until(self):
        return self.end_at.astimezone(UTC) + timedelta(minutes=self.buffer_minutes)

    @property
    def conflict_rows(self):
        from django.utils import timezone

        from .google_api import parse_instant

        state = self.remote_conflict
        rows = []
        for key, label in [
            ("start", "Google-Beginn"),
            ("end", "Google-Ende"),
            ("title", "Google-Titel"),
            ("notes", "Google-Notizen"),
            ("reason", "Hinweis"),
        ]:
            if key in state:
                value = state[key]
                if key in ["start", "end"]:
                    value = timezone.localtime(parse_instant(value)).strftime("%d.%m.%Y, %H:%M Uhr")
                rows.append({"label": label, "value": value})
        if state.get("cancelled"):
            rows.append({"label": "Google-Status", "value": "Abgesagt / gelöscht"})
        return rows

    def __str__(self):
        return f"{self.appointment_type} · {self.customer}"


class RemoteBusinessEvent(models.Model):
    connection = models.ForeignKey(CalendarConnection, on_delete=models.CASCADE)
    remote_id = models.CharField(max_length=1024)
    title = models.CharField(max_length=300)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["connection", "remote_id"], name="calendar_unique_external_event"
            )
        ]
        ordering = ["start_at"]


class PrivateBusy(models.Model):
    """Absichtlich keine Felder für private Titel, Teilnehmer oder Beschreibungen."""

    connection = models.ForeignKey(CalendarConnection, on_delete=models.CASCADE)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()

    class Meta:
        ordering = ["start_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["connection", "start_at", "end_at"], name="calendar_unique_private_busy"
            )
        ]
