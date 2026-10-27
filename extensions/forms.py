from django import forms

from .models import ExtensionPosition

POSITION_FIELDS = [
    "manufacturer",
    "extension_type",
    "color",
    "color_code",
    "length_cm",
    "weight_g",
    "quantity",
    "quantity_unit",
    "purchase_price",
    "sale_price",
    "assigned_on",
    "delivery_status",
    "notes",
]
SUGGESTION_FIELDS = ["manufacturer", "extension_type", "color", "color_code"]


class PositionForm(forms.ModelForm):
    version = forms.IntegerField(widget=forms.HiddenInput, required=False, min_value=1)

    class Meta:
        model = ExtensionPosition
        fields = POSITION_FIELDS
        widgets = {
            "assigned_on": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["version"].initial = self.instance.version
        self.fields["assigned_on"].input_formats = ["%Y-%m-%d", "%d.%m.%Y"]
        for name in ["length_cm", "weight_g", "purchase_price", "sale_price"]:
            self.fields[name].localize = True
            self.fields[name].widget = forms.TextInput(attrs={"inputmode": "decimal"})
        for name in SUGGESTION_FIELDS:
            self.fields[name].widget.attrs["list"] = f"suggestions-{name}"
        self.fields[
            "purchase_price"
        ].help_text = "Gesamtpreis dieser Position; kein Preis je Gramm oder Packung."
        self.fields["quantity_unit"].choices = [("", "Keine zusätzliche Anzahl")] + list(
            ExtensionPosition.Unit.choices
        )
        self.fields["delivery_status"].choices = [("", "Nicht hinterlegt")] + list(
            ExtensionPosition.Delivery.choices
        )
        for name, field in self.fields.items():
            field.widget.attrs["aria-describedby"] = f"{name}-help {name}-errors"

    def clean(self):
        data = super().clean()
        if bool(data.get("quantity")) != bool(data.get("quantity_unit")):
            self.add_error(
                "quantity", "Bitte Anzahl und Einheit gemeinsam angeben oder beide leer lassen."
            )
        if not self.instance._state.adding and not data.get("version"):
            self.add_error(None, "Der Bearbeitungsstand fehlt. Bitte öffne die Position erneut.")
        return data
