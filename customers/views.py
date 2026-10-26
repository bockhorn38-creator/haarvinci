import json
import unicodedata

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from .forms import CustomerForm
from .models import Customer
from .services import EditConflict, update_customer


@login_required
@require_GET
def customer_list(request):
    customers = Customer.objects.for_user(request.user)
    count = customers.count()
    query = request.GET.get("q", "").strip()[:200]
    for term in query.split():
        match = Q(search_text__contains=unicodedata.normalize("NFKC", term).casefold())
        digits = "".join(c for c in term if c.isdigit())
        if digits:
            match |= Q(phone_digits__contains=digits)
        customers = customers.filter(match)
    page = Paginator(customers, 12).get_page(request.GET.get("seite"))
    return render(
        request,
        "customers/list.html",
        {"nav": "customers", "page": page, "query": query, "total": count},
    )


@login_required
@require_GET
def customer_detail(request, pk):
    customer = get_object_or_404(Customer.objects.for_user(request.user), pk=pk)
    return render(request, "customers/detail.html", {"nav": "customers", "customer": customer})


@login_required
@require_http_methods(["GET", "POST"])
def customer_create(request):
    form = CustomerForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        customer = form.save(commit=False)
        customer.owner = request.user
        customer.save()
        messages.success(request, f"Die Kundenakte für {customer} wurde angelegt.")
        return redirect("customers:detail", pk=customer.pk)
    return render(
        request, "customers/form.html", {"nav": "customers", "form": form, "editing": False}
    )


@login_required
@require_http_methods(["GET", "POST"])
def customer_edit(request, pk):
    customer = get_object_or_404(Customer.objects.for_user(request.user), pk=pk)
    form = CustomerForm(request.POST if request.method == "POST" else None, instance=customer)
    status = 200
    if request.method == "POST" and form.is_valid():
        try:
            customer = update_customer(
                customer_id=pk, user=request.user, cleaned_data=form.cleaned_data
            )
        except EditConflict:
            form.add_error(
                None,
                "Diese Akte wurde inzwischen geändert. Deine Eingaben bleiben hier sichtbar. Öffne die aktuelle Akte in einem neuen Tab und übernimm deine Änderungen dort.",
            )
            status = 409
        else:
            messages.success(request, "Die Änderungen wurden gespeichert.")
            return redirect("customers:detail", pk=customer.pk)
    return render(
        request,
        "customers/form.html",
        {"nav": "customers", "form": form, "editing": True, "customer": customer},
        status=status,
    )


@login_required
@require_GET
def customer_export(request, pk):
    customer = get_object_or_404(Customer.objects.for_user(request.user), pk=pk)
    fields = [
        "id",
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
        "created_at",
        "updated_at",
    ]
    data = {field: getattr(customer, field) for field in fields}
    response = HttpResponse(
        json.dumps(
            {"format_version": 1, "customer": data}, ensure_ascii=False, indent=2, default=str
        ),
        content_type="application/json; charset=utf-8",
    )
    response["Content-Disposition"] = f'attachment; filename="haarvinci-kundin-{customer.pk}.json"'
    return response
