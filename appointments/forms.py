from datetime import UTC, datetime
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from django import forms
from django.db.models import Q
from django.utils import timezone

from customers.models import Customer

from .models import Appointment, AppointmentType, CalendarConnection, CalendarSettings

BERLIN = ZoneInfo("Europe/Berlin")


def berlin_time(day, clock):
    wall = datetime.combine(day, clock)
    a, b = (wall.replace(tzinfo=BERLIN, fold=fold) for fold in [0, 1])
    if (
        a.utcoffset() != b.utcoffset()
        or a.astimezone(UTC).astimezone(BERLIN).replace(tzinfo=None) != wall
    ):
        raise forms.ValidationError(
            "Diese Uhrzeit ist wegen der Zeitumstellung nicht eindeutig oder existiert nicht. Bitte wähle eine andere Uhrzeit."
        )
    return a


class AppointmentForm(forms.ModelForm):
    day = forms.DateField(
        label="Datum", widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"})
    )
    begin = forms.TimeField(
        label="Beginn", widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"})
    )
    finish = forms.TimeField(
        label="Ende", widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"})
    )
    end_day = forms.DateField(
        label="Abweichendes Enddatum",
        required=False,
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
    )
    version = forms.IntegerField(widget=forms.HiddenInput, min_value=1, required=False)
    allow_overlap = forms.BooleanField(
        label="Die angezeigte Überschneidung bewusst übernehmen", required=False
    )

    class Meta:
        model = Appointment
        fields = ["customer", "appointment_type", "buffer_minutes", "notes", "status"]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
            "buffer_minutes": forms.NumberInput(
                attrs={"min": 0, "max": 240, "inputmode": "numeric"}
            ),
        }

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["customer"].queryset = Customer.objects.for_user(user)
        self.fields["appointment_type"].queryset = AppointmentType.objects.filter(
            Q(owner=user) | Q(owner__isnull=True)
        )
        self.fields["version"].initial = self.instance.version
        if self.instance.pk and not self.instance._state.adding:
            start, end = (
                timezone.localtime(self.instance.start_at, BERLIN),
                timezone.localtime(self.instance.end_at, BERLIN),
            )
            self.initial.update(
                day=start.date(),
                begin=start.time(),
                finish=end.time(),
                end_day=end.date() if end.date() != start.date() else None,
            )
        for name in ["day", "end_day"]:
            self.fields[name].input_formats = ["%Y-%m-%d", "%d.%m.%Y"]
        for name in ["begin", "finish"]:
            self.fields[name].input_formats = ["%H:%M"]
        for name, field in self.fields.items():
            field.widget.attrs["aria-describedby"] = f"{name}-help {name}-errors"

    def clean(self):
        data = super().clean()
        if not self.instance._state.adding and not data.get("version"):
            self.add_error(None, "Der Bearbeitungsstand fehlt. Bitte öffne den Termin erneut.")
        if all(data.get(key) for key in ["day", "begin", "finish"]):
            try:
                start = berlin_time(data["day"], data["begin"])
                end = berlin_time(data.get("end_day") or data["day"], data["finish"])
                if not 2000 <= start.year <= 2100 or not 2000 <= end.year <= 2100:
                    raise forms.ValidationError("Bitte ein Datum zwischen 2000 und 2100 wählen.")
                if end.astimezone(UTC) <= start.astimezone(UTC):
                    raise forms.ValidationError("Das Ende muss nach dem Beginn liegen.")
                if (end.astimezone(UTC) - start.astimezone(UTC)).total_seconds() > 24 * 3600:
                    raise forms.ValidationError("Ein Termin darf höchstens 24 Stunden dauern.")
                if data.get("status") == Appointment.Status.COMPLETED and end > timezone.now():
                    raise forms.ValidationError(
                        "Ein zukünftiger Termin kann noch nicht als abgeschlossen zählen."
                    )
                data["start_at"], data["end_at"] = start, end
            except forms.ValidationError as error:
                self.add_error(None, error)
        return data


def validate_broker_url(value):
    if not value:
        return value
    parts = urlsplit(value)
    if (
        parts.scheme != "https"
        or not parts.hostname
        or parts.username
        or parts.password
        or parts.query
        or parts.fragment
        or parts.path not in ["", "/"]
        or parts.port not in [None, 443]
    ):
        raise forms.ValidationError(
            "Bitte nur die HTTPS-Basisadresse deines eigenen Anmeldedienstes angeben, ohne Pfad oder Zugangsdaten."
        )
    return value.rstrip("/")


class GoogleSettingsForm(forms.ModelForm):
    class Meta:
        model = CalendarSettings
        fields = ["broker_url"]
        widgets = {
            "broker_url": forms.URLInput(attrs={"placeholder": "https://anmeldung.deine-domain.de"})
        }

    def clean_broker_url(self):
        value = validate_broker_url(self.cleaned_data["broker_url"])
        if (
            self.instance.pk
            and value != self.instance.broker_url
            and CalendarConnection.objects.filter(owner=self.instance.owner)
            .exclude(state=CalendarConnection.State.DISCONNECTED)
            .exists()
        ):
            raise forms.ValidationError(
                "Bitte zuerst beide Google-Verbindungen trennen, bevor du den Anmeldedienst änderst."
            )
        return value


class TypeForm(forms.ModelForm):
    class Meta:
        model = AppointmentType
        fields = ["name"]
