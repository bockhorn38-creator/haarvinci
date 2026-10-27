import unicodedata
from decimal import Decimal

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from customers.models import Customer
from customers.services import EditConflict

from .forms import SUGGESTION_FIELDS, PositionForm
from .models import ExtensionPosition
from .services import create_position, delete_position, update_position


@login_required
@require_GET
def position_list(request):
    positions = ExtensionPosition.objects.for_user(request.user).select_related("customer")
    query = request.GET.get("q", "").strip()[:200]
    status = request.GET.get("status", "")
    if status in ExtensionPosition.Delivery.values:
        positions = positions.filter(delivery_status=status)
    else:
        status = ""
    for term in query.split():
        normalized = unicodedata.normalize("NFKC", term).casefold()
        positions = positions.filter(
            Q(search_text__contains=normalized) | Q(customer__search_text__contains=normalized)
        )
    totals = positions.aggregate(purchase=Sum("purchase_price"))
    return render(
        request,
        "extensions/list.html",
        {
            "nav": "extensions",
            "page": Paginator(positions, 12).get_page(request.GET.get("seite")),
            "query": query,
            "status": status,
            "statuses": ExtensionPosition.Delivery.choices,
            "purchase_total": totals["purchase"] or Decimal("0.00"),
        },
    )


def suggestions(user):
    positions = ExtensionPosition.objects.for_user(user)
    return {
        field: list(
            positions.exclude(**{field: ""})
            .order_by(field)
            .values_list(field, flat=True)
            .distinct()[:50]
        )
        for field in SUGGESTION_FIELDS
    }


@login_required
@require_http_methods(["GET", "POST"])
def position_create(request, customer_pk):
    customer = get_object_or_404(Customer.objects.for_user(request.user), pk=customer_pk)
    form = PositionForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        create_position(customer_id=customer.pk, user=request.user, cleaned_data=form.cleaned_data)
        messages.success(request, "Die Extensions wurden der Kundin zugeordnet.")
        return redirect("customers:detail", pk=customer.pk)
    return render(
        request,
        "extensions/form.html",
        {
            "nav": "extensions",
            "customer": customer,
            "form": form,
            "editing": False,
            "suggestions": suggestions(request.user),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def position_edit(request, customer_pk, pk):
    position = get_object_or_404(
        ExtensionPosition.objects.for_user(request.user).select_related("customer"),
        pk=pk,
        customer_id=customer_pk,
    )
    form = PositionForm(request.POST if request.method == "POST" else None, instance=position)
    status = 200
    if request.method == "POST" and form.is_valid():
        try:
            update_position(
                customer_id=customer_pk,
                position_id=pk,
                user=request.user,
                cleaned_data=form.cleaned_data,
            )
        except ExtensionPosition.DoesNotExist as error:
            raise Http404 from error
        except EditConflict:
            form.add_error(
                None,
                "Diese Position wurde inzwischen geändert. Deine Eingaben bleiben sichtbar. Öffne die Position erneut, bevor du sie übernimmst.",
            )
            status = 409
        else:
            messages.success(
                request, "Die Extensions wurden aktualisiert. Die Änderung steht in der Historie."
            )
            return redirect("customers:detail", pk=customer_pk)
    return render(
        request,
        "extensions/form.html",
        {
            "nav": "extensions",
            "customer": position.customer,
            "position": position,
            "form": form,
            "editing": True,
            "suggestions": suggestions(request.user),
        },
        status=status,
    )


class DeleteForm(forms.Form):
    version = forms.IntegerField(widget=forms.HiddenInput, min_value=1)


@login_required
@require_http_methods(["GET", "POST"])
def position_delete(request, customer_pk, pk):
    position = get_object_or_404(
        ExtensionPosition.objects.for_user(request.user).select_related("customer"),
        pk=pk,
        customer_id=customer_pk,
    )
    form = DeleteForm(
        request.POST if request.method == "POST" else None, initial={"version": position.version}
    )
    status = 200
    if request.method == "POST" and form.is_valid():
        try:
            delete_position(
                customer_id=customer_pk,
                position_id=pk,
                user=request.user,
                version=form.cleaned_data["version"],
            )
        except ExtensionPosition.DoesNotExist as error:
            raise Http404 from error
        except EditConflict:
            form.add_error(
                None,
                "Diese Position wurde inzwischen geändert. Bitte prüfe die aktuelle Position erneut.",
            )
            status = 409
        else:
            messages.success(
                request,
                "Die Extensions-Position wurde gelöscht. Ihr bisheriger Stand bleibt in der Historie erhalten.",
            )
            return redirect("customers:detail", pk=customer_pk)
    return render(
        request,
        "extensions/delete.html",
        {
            "nav": "extensions",
            "position": position,
            "customer": position.customer,
            "form": form,
        },
        status=status,
    )
