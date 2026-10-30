from django.db import transaction
from django.utils import timezone

from customers.models import Customer, CustomerEvent
from customers.services import EditConflict, changed_fields, field_snapshot

from .forms import POSITION_FIELDS
from .models import ExtensionPosition


def record_event(*, position, user, kind, before=None):
    after = field_snapshot(position, POSITION_FIELDS)
    CustomerEvent.objects.create(
        customer=position.customer,
        actor=user,
        kind=kind,
        occurred_on=position.assigned_on
        if kind == CustomerEvent.Kind.EXTENSION_CREATED
        else timezone.localdate(),
        extension_uuid=position.pk,
        summary=str(position),
        snapshot=after,
        changes=changed_fields(ExtensionPosition, before, after) if before else [],
    )


@transaction.atomic
def create_position(*, customer_id, user, cleaned_data, position_id=None):
    customer = Customer.objects.for_user(user).select_for_update().get(pk=customer_id)
    position = ExtensionPosition.objects.create(
        **({"id": position_id} if position_id else {}),
        customer=customer,
        **{name: cleaned_data[name] for name in POSITION_FIELDS},
    )
    record_event(position=position, user=user, kind=CustomerEvent.Kind.EXTENSION_CREATED)
    return position


@transaction.atomic
def update_position(*, customer_id, position_id, user, cleaned_data):
    Customer.objects.for_user(user).select_for_update().get(pk=customer_id)
    position = (
        ExtensionPosition.objects.for_user(user)
        .select_for_update()
        .get(pk=position_id, customer_id=customer_id)
    )
    if position.version != cleaned_data.get("version"):
        raise EditConflict
    before = field_snapshot(position, POSITION_FIELDS)
    for name in POSITION_FIELDS:
        setattr(position, name, cleaned_data[name])
    position.version += 1
    position.save()
    if before != field_snapshot(position, POSITION_FIELDS):
        record_event(
            position=position, user=user, kind=CustomerEvent.Kind.EXTENSION_UPDATED, before=before
        )
    return position


@transaction.atomic
def delete_position(*, customer_id, position_id, user, version):
    Customer.objects.for_user(user).select_for_update().get(pk=customer_id)
    position = (
        ExtensionPosition.objects.for_user(user)
        .select_for_update()
        .get(pk=position_id, customer_id=customer_id)
    )
    if position.version != version:
        raise EditConflict
    record_event(position=position, user=user, kind=CustomerEvent.Kind.EXTENSION_DELETED)
    position.delete()
