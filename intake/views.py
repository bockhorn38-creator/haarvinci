from django import forms
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods

from customers.services import EditConflict
from treatments.services import BusinessError

from .models import ImportReceipt
from .parser import ImportProblem
from .services import commit, find, prepare, review


class PasteForm(forms.Form):
    text = forms.CharField(
        label="Haarvinci-Importtext",
        max_length=65536,
        widget=forms.Textarea(
            attrs={
                "rows": 12,
                "spellcheck": "false",
                "placeholder": "Hier die strukturierte ChatGPT-Antwort einfügen …",
            }
        ),
    )


def allowed():
    if not settings.DEBUG and not getattr(settings, "DESKTOP_MODE", False):
        raise PermissionDenied


@login_required
@require_http_methods(["GET", "POST"])
def start(request):
    allowed()
    form = PasteForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            draft, receipt = prepare(
                request.user, request.session.session_key, form.cleaned_data["text"]
            )
        except ImportProblem as error:
            form.add_error("text", str(error))
        else:
            return redirect(
                "intake:receipt" if receipt else "intake:draft",
                pk=receipt.pk if receipt else draft.key,
            )
    return render(request, "intake/start.html", {"nav": "account", "form": form})


@login_required
@require_http_methods(["GET", "POST"])
def draft_view(request, pk):
    allowed()
    try:
        draft = find(pk, request.user, request.session.session_key)
    except ImportProblem as error:
        return render(
            request, "intake/expired.html", {"nav": "account", "problem": str(error)}, status=410
        )
    error = ""
    with draft.lock:
        if draft.receipt_id:
            return redirect("intake:receipt", pk=draft.receipt_id)
        if request.method == "POST" and request.POST.get("action") == "confirm":
            try:
                receipt = commit(draft, request.user, request.POST.get("confirmation", ""))
            except (ImportProblem, EditConflict, BusinessError, ValidationError) as problem:
                error = (
                    str(problem) or "Der Datenstand wurde inzwischen geändert. Bitte erneut prüfen."
                )
            else:
                return redirect("intake:receipt", pk=receipt.pk)
        posted = (
            request.POST
            if request.method == "POST" and request.POST.get("action") == "review"
            else None
        )
        result = review(draft, request.user, posted)
        if error:
            result["ready"] = False
            draft.plan, draft.confirmation = None, ""
        return render(
            request,
            "intake/ready.html" if result["ready"] else "intake/draft.html",
            {"nav": "account", "draft": draft, "result": result, "problem": error},
        )


@login_required
@require_GET
def receipt(request, pk):
    saved = get_object_or_404(ImportReceipt.objects.filter(owner=request.user), pk=pk)
    return render(request, "intake/receipt.html", {"nav": "account", "receipt": saved})


def native_prepare(cookies, text):
    import json
    from http.cookies import SimpleCookie

    from django.db import close_old_connections

    from appointments.native import authenticated_user

    close_old_connections()
    try:
        user = authenticated_user(cookies)
        jar = SimpleCookie()
        jar.load(cookies)
        session = jar[settings.SESSION_COOKIE_NAME].value
        draft, saved = prepare(user, session, text)
        return json.dumps(
            {
                "path": reverse("intake:receipt", args=[saved.pk])
                if saved
                else reverse("intake:draft", args=[draft.key])
            }
        )
    except ImportProblem as error:
        return json.dumps({"message": str(error)})
    except Exception:
        return json.dumps(
            {
                "message": "Bitte zuerst in Haarvinci anmelden und den Text anschließend erneut teilen oder einfügen."
            }
        )
    finally:
        close_old_connections()
