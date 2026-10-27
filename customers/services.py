from django.db import transaction
from django.utils import timezone

from .forms import CUSTOMER_FIELDS
from .history import display_value
from .models import Customer, CustomerEvent


class EditConflict(Exception):
    pass


def field_snapshot(instance, fields):
    return {
        field: str(value) if (value := getattr(instance, field)) is not None else ""
        for field in fields
    }


def changed_fields(model, before, after):
    return [
        {
            "field": name,
            "label": str(model._meta.get_field(name).verbose_name),
            "before": display_value(model._meta.get_field(name), before[name]),
            "after": display_value(model._meta.get_field(name), after[name]),
        }
        for name in before
        if before[name] != after[name]
    ]


@transaction.atomic
def create_customer(*, user, cleaned_data):
    customer = Customer.objects.create(
        owner=user, **{name: cleaned_data[name] for name in CUSTOMER_FIELDS}
    )
    CustomerEvent.objects.create(
        customer=customer,
        actor=user,
        kind=CustomerEvent.Kind.CREATED,
        occurred_on=timezone.localdate(),
        summary=str(customer),
        snapshot=field_snapshot(customer, CUSTOMER_FIELDS),
    )
    return customer


@transaction.atomic
def update_customer(*, customer_id, user, cleaned_data):
    """Änderungen zweier geöffneter Formulare niemals still überschreiben."""
    customer = Customer.objects.for_user(user).select_for_update().get(pk=customer_id)
    if customer.version != cleaned_data.get("version"):
        raise EditConflict
    before = field_snapshot(customer, CUSTOMER_FIELDS)
    for field in CUSTOMER_FIELDS:
        setattr(customer, field, cleaned_data[field])
    customer.version += 1
    customer.save()
    after = field_snapshot(customer, CUSTOMER_FIELDS)
    changes = changed_fields(Customer, before, after)
    if changes:
        CustomerEvent.objects.create(
            customer=customer,
            actor=user,
            kind=CustomerEvent.Kind.PROFILE,
            occurred_on=timezone.localdate(),
            summary=str(customer),
            snapshot=after,
            changes=changes,
        )
    return customer
