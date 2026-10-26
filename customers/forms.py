import re

from django import forms
from django.utils import timezone

from .models import Customer


class CustomerForm(forms.ModelForm):
    version = forms.IntegerField(widget=forms.HiddenInput, required=False)

    class Meta:
        model = Customer
        fields = [
            "first_name",
            "last_name",
            "phone",
            "email",
            "street",
            "postal_code",
            "city",
            "birthday",
            "first_consultation",
            "notes",
        ]
        widgets = {
            "first_name": forms.TextInput(
                attrs={"autocomplete": "given-name", "placeholder": "z. B. Marie"}
            ),
            "last_name": forms.TextInput(
                attrs={"autocomplete": "family-name", "placeholder": "z. B. Sommer"}
            ),
            "phone": forms.TextInput(
                attrs={"type": "tel", "autocomplete": "tel", "placeholder": "+49 …"}
            ),
            "email": forms.EmailInput(
                attrs={"autocomplete": "email", "placeholder": "name@beispiel.de"}
            ),
            "street": forms.TextInput(attrs={"autocomplete": "street-address"}),
            "postal_code": forms.TextInput(attrs={"autocomplete": "postal-code"}),
            "city": forms.TextInput(attrs={"autocomplete": "address-level2"}),
            "birthday": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "first_consultation": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "notes": forms.Textarea(
                attrs={"rows": 5, "placeholder": "Was möchtest du dir für diese Kundin merken?"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["version"].initial = (
            self.instance.version if not self.instance._state.adding else 1
        )
        for name, field in self.fields.items():
            field.widget.attrs["aria-describedby"] = f"{name}-help {name}-errors"
        self.fields["birthday"].input_formats = ["%Y-%m-%d", "%d.%m.%Y"]
        self.fields["first_consultation"].input_formats = ["%Y-%m-%d", "%d.%m.%Y"]

    def clean(self):
        data = super().clean()
        for name in ["first_name", "last_name", "phone", "street", "postal_code", "city"]:
            if name in data:
                data[name] = data[name].strip()
        if not data.get("phone") and not data.get("email"):
            self.add_error("phone", "Bitte gib eine Telefonnummer oder E-Mail-Adresse an.")
        phone = data.get("phone", "")
        if phone and (
            not re.fullmatch(r"[+\d\s()/.-]+", phone) or len(re.sub(r"\D", "", phone)) < 5
        ):
            self.add_error("phone", "Bitte gib eine gültige Telefonnummer ein.")
        if data.get("email"):
            data["email"] = data["email"].lower()
        birthday = data.get("birthday")
        consultation = data.get("first_consultation")
        if birthday and birthday > timezone.localdate():
            self.add_error("birthday", "Das Geburtsdatum darf nicht in der Zukunft liegen.")
        if birthday and consultation and birthday > consultation:
            self.add_error("first_consultation", "Die Beratung muss nach dem Geburtsdatum liegen.")
        if not self.instance._state.adding and not data.get("version"):
            self.add_error(None, "Der Bearbeitungsstand fehlt. Bitte lade die Kundenakte neu.")
        return data
