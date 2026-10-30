import uuid

from django import forms
from django.utils import timezone

from appointments.models import Appointment
from customers.models import Customer
from extensions.models import ExtensionPosition

from .models import MAX_MONEY, Payment, PriceOption, Treatment


def money(label, required=True):
    return forms.DecimalField(
        label=label,
        required=required,
        min_value=0,
        max_value=MAX_MONEY,
        max_digits=9,
        decimal_places=2,
        localize=True,
        widget=forms.TextInput(attrs={"inputmode": "decimal"}),
    )


class PriceForm(forms.ModelForm):
    version = forms.IntegerField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = PriceOption
        fields = ["name", "category", "rows", "price", "active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["price"] = money("Gesamtpreis (€)")
        self.fields["version"].initial = self.instance.version

    def clean(self):
        data = super().clean()
        if data.get("category") == "weaving" and not data.get("rows"):
            self.add_error("rows", "Bitte die Reihenanzahl angeben.")
        if data.get("category") == "service" and data.get("rows"):
            self.add_error("rows", "Zusatzleistungen haben keine Weaving-Reihenanzahl.")
        return data


class TreatmentForm(forms.Form):
    customer = forms.ModelChoiceField(label="Kundin", queryset=Customer.objects.none())
    appointment = forms.ModelChoiceField(
        label="Zugehöriger Termin", queryset=Appointment.objects.none(), required=False
    )
    performed_on = forms.DateField(
        label="Behandlungsdatum", widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"})
    )
    description = forms.CharField(label="Behandlung", max_length=200)
    status = forms.ChoiceField(
        label="Status",
        choices=[choice for choice in Treatment.Status.choices if choice[0] != "cancelled"],
    )
    rows = forms.IntegerField(label="Weaving-Reihen", min_value=1, max_value=20, required=False)
    price_mode = forms.ChoiceField(
        label="Preisvereinbarung",
        choices=[
            ("weaving", "Weaving-Preisliste + Zusatzleistungen"),
            ("individual", "Individueller Gesamtpreis"),
        ],
    )
    custom_price = money("Individueller Gesamtpreis inklusive aller Leistungen (€)", required=False)
    services = forms.ModelMultipleChoiceField(
        label="Zusatzleistungen",
        queryset=PriceOption.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    extensions = forms.ModelMultipleChoiceField(
        label="Zugeordnete Extensions",
        queryset=ExtensionPosition.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    charge_extensions = forms.BooleanField(
        label="Verkaufspreise der gewählten Extensions zusätzlich berechnen",
        required=False,
        help_text="Nur wählen, wenn sie nicht bereits im vereinbarten Preis enthalten sind.",
    )
    notes = forms.CharField(
        label="Behandlungsdokumentation",
        max_length=10000,
        required=False,
        widget=forms.Textarea(attrs={"rows": 5}),
    )
    version = forms.IntegerField(required=False, widget=forms.HiddenInput)
    quote_digest = forms.CharField(required=False, widget=forms.HiddenInput)

    def __init__(self, *args, user, customer=None, instance=None, **kwargs):
        self.instance = instance
        super().__init__(*args, **kwargs)
        self.fields["customer"].queryset = Customer.objects.for_user(user)
        people = (
            Customer.objects.filter(pk=customer.pk) if customer else Customer.objects.for_user(user)
        )
        self.fields["appointment"].queryset = (
            Appointment.objects.for_user(user)
            .filter(customer__in=people)
            .exclude(status="cancelled")
            .select_related("customer", "appointment_type")
        )
        self.fields["extensions"].queryset = ExtensionPosition.objects.for_user(user).filter(
            customer__in=people
        )
        self.fields["services"].queryset = PriceOption.objects.for_user(user).filter(
            category="service", active=True
        )
        if instance:
            self.fields["services"].queryset = PriceOption.objects.for_user(user).filter(
                category="service"
            )
            self.fields["price_mode"].choices = [
                ("keep", "Bisherige Preisvereinbarung beibehalten"),
                *self.fields["price_mode"].choices,
            ]
        self.fields["performed_on"].input_formats = ["%Y-%m-%d", "%d.%m.%Y"]

    def clean(self):
        data = super().clean()
        person = data.get("customer")
        appointment = data.get("appointment")
        if appointment and person and appointment.customer_id != person.pk:
            self.add_error("appointment", "Dieser Termin gehört zu einer anderen Kundin.")
        if (
            any(position.customer_id != person.pk for position in data.get("extensions", []))
            if person
            else False
        ):
            self.add_error("extensions", "Alle Extensions müssen derselben Kundin gehören.")
        if data.get("performed_on") and not 2000 <= data["performed_on"].year <= 2100:
            self.add_error(
                "performed_on", "Bitte ein Behandlungsdatum zwischen 2000 und 2100 wählen."
            )
        if data.get("status") == "completed":
            if data.get("performed_on") and data["performed_on"] > timezone.localdate():
                self.add_error(
                    "performed_on", "Eine zukünftige Behandlung kann noch nicht durchgeführt sein."
                )
            if appointment and appointment.end_at > timezone.now():
                self.add_error(
                    "appointment",
                    "Dieser Termin ist noch nicht beendet. Bitte zunächst als geplant speichern.",
                )
        if data.get("price_mode") == "weaving" and not data.get("rows"):
            self.add_error("rows", "Bitte die Reihenanzahl für die Preisberechnung angeben.")
        if data.get("price_mode") == "individual" and data.get("custom_price") is None:
            self.add_error(
                "custom_price", "Bitte den individuell vereinbarten Gesamtpreis angeben."
            )
        if self.instance and not data.get("version"):
            self.add_error(None, "Der Bearbeitungsstand fehlt. Bitte erneut öffnen.")
        return data


class PaymentForm(forms.Form):
    amount = money("Betrag (€)")
    booked_on = forms.DateField(
        label="Zahlungsdatum", widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"})
    )
    method = forms.ChoiceField(label="Zahlungsweg", choices=Payment.Method.choices)
    purpose = forms.ChoiceField(label="Buchungsart", choices=Payment.Purpose.choices[:3])
    original = forms.ModelChoiceField(
        label="Ursprünglicher Zahlungseingang", queryset=Payment.objects.none(), required=False
    )
    notes = forms.CharField(
        label="Notiz / Erstattungsgrund",
        max_length=2000,
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    booking_key = forms.UUIDField(widget=forms.HiddenInput, initial=uuid.uuid4)
    version = forms.IntegerField(widget=forms.HiddenInput, required=False)

    def __init__(self, *args, user, treatment=None, refund=False, imported=False, **kwargs):
        self.refund = refund
        super().__init__(*args, **kwargs)
        self.fields["booked_on"].input_formats = ["%Y-%m-%d", "%d.%m.%Y"]
        if refund:
            self.fields["purpose"].choices = [("refund", "Rückerstattung")]
            self.fields["original"].required = not imported
            self.fields["notes"].required = True
        else:
            self.fields.pop("original")
        if treatment:
            self.fields.get("original", forms.Field()).queryset = Payment.objects.for_user(
                user
            ).filter(treatment=treatment, kind="receipt", state="posted")
        if imported:
            self.fields["booking_key"].required = False

    def clean_amount(self):
        value = self.cleaned_data["amount"]
        if value <= 0:
            raise forms.ValidationError("Der Betrag muss größer als null sein.")
        return value

    def clean_booked_on(self):
        value = self.cleaned_data["booked_on"]
        if not 2000 <= value.year <= 2100 or value > timezone.localdate():
            raise forms.ValidationError("Bitte ein tatsächliches Zahlungsdatum bis heute angeben.")
        return value


class DecisionForm(forms.Form):
    version = forms.IntegerField(widget=forms.HiddenInput, min_value=1)
    reason = forms.CharField(
        label="Grund", max_length=1000, widget=forms.Textarea(attrs={"rows": 3})
    )
