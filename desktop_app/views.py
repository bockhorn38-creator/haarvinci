from django import forms
from django.contrib.auth import get_user_model, login
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from customers.management.commands.init_demo import DEMO
from customers.models import Customer


class FirstRunForm(UserCreationForm):
    first_name = forms.CharField(label="Dein Vorname", initial="Conny", max_length=80)
    demo_data = forms.BooleanField(
        label="Mit sechs fiktiven Testkundinnen starten", required=False, initial=True
    )

    class Meta(UserCreationForm.Meta):
        fields = ["first_name", "username"]
        labels = {"username": "Dein Benutzername"}
        widgets = {
            "username": forms.TextInput(
                attrs={"autocomplete": "username", "autocapitalize": "none"}
            )
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].initial = "conny"
        self.fields["password2"].label = "Passwort wiederholen"


@require_http_methods(["GET", "POST"])
def first_run(request):
    User = get_user_model()
    if User.objects.exists():
        raise Http404
    form = FirstRunForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            if User.objects.exists():
                raise Http404
            user = form.save()
            if form.cleaned_data["demo_data"]:
                for first, last, phone, email, consultation, notes in DEMO:
                    Customer.objects.create(
                        owner=user,
                        first_name=first,
                        last_name=last,
                        phone=phone,
                        email=email,
                        first_consultation=consultation,
                        notes=notes,
                    )
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return redirect("dashboard")
    return render(request, "registration/desktop_setup.html", {"form": form})
