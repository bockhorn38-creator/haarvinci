from django.db import transaction

from .models import Customer


class EditConflict(Exception):
    pass


@transaction.atomic
def update_customer(*, customer_id, user, cleaned_data):
    """Änderungen zweier geöffneter Formulare niemals still überschreiben."""
    customer = Customer.objects.for_user(user).select_for_update().get(pk=customer_id)
    if customer.version != cleaned_data.get("version"):
        raise EditConflict
    editable = [
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
    for field in editable:
        setattr(customer, field, cleaned_data[field])
    customer.version += 1
    customer.save()
    return customer
