from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Q, Sum
from django.utils import timezone

from appointments.models import Appointment

from .models import ZERO, Payment, Treatment


def report(user, customer=None, start=None, end=None):
    treatments = Treatment.objects.for_user(user).select_related("customer", "appointment")
    payments = Payment.objects.for_user(user).filter(state="posted")
    if customer:
        treatments = treatments.filter(customer=customer)
        payments = payments.filter(treatment__customer=customer)
    all_items = list(
        treatments.annotate(
            received_value=Sum(
                "payments__amount",
                filter=Q(payments__kind="receipt", payments__state="posted"),
                default=ZERO,
            ),
            refunded_value=Sum(
                "payments__amount",
                filter=Q(payments__kind="refund", payments__state="posted"),
                default=ZERO,
            ),
        )
    )
    outstanding, refund_due = ZERO, ZERO
    debtors, refunds = [], []
    for item in all_items:
        item.paid_value = item.received_value - item.refunded_value
        item.open_value = (
            max(ZERO, item.total - item.paid_value) if item.status != "cancelled" else ZERO
        )
        item.refund_value = item.paid_value if item.status == "cancelled" else ZERO
        outstanding += item.open_value
        refund_due += item.refund_value
        if item.open_value:
            debtors.append(item)
        if item.refund_value:
            refunds.append(item)
    period_items = [
        item
        for item in all_items
        if (not start or item.performed_on >= start) and (not end or item.performed_on <= end)
    ]
    completed = [item for item in period_items if item.status == "completed"]
    if start:
        payments = payments.filter(booked_on__gte=start)
    if end:
        payments = payments.filter(booked_on__lte=end)
    values = payments.aggregate(
        receipts=Sum("amount", filter=Q(kind="receipt"), default=ZERO),
        refunds=Sum("amount", filter=Q(kind="refund"), default=ZERO),
        deposits=Sum("amount", filter=Q(kind="receipt", purpose="deposit"), default=ZERO),
    )
    value = sum((item.total for item in completed), ZERO)
    legacy = Appointment.objects.for_user(user).filter(
        status="completed", end_at__lte=timezone.now(), treatment__isnull=True
    )
    if customer:
        legacy = legacy.filter(customer=customer)
    if start:
        legacy = legacy.filter(start_at__date__gte=start)
    if end:
        legacy = legacy.filter(start_at__date__lte=end)
    return {
        "completed_count": len(completed),
        "visits": len(completed) + legacy.count(),
        "planned_count": sum(item.status == "planned" for item in period_items),
        "completed_value": value,
        "average_value": (value / len(completed)).quantize(Decimal(".01"), rounding=ROUND_HALF_UP)
        if completed
        else ZERO,
        "receipts": values["receipts"],
        "refunds": values["refunds"],
        "deposits": values["deposits"],
        "net_received": values["receipts"] - values["refunds"],
        "outstanding": outstanding,
        "refund_due": refund_due,
        "debtors": debtors,
        "refund_items": refunds,
        "treatments": period_items,
        "payments": payments.select_related("treatment__customer")[:100],
    }
