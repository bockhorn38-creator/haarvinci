from django import template
from django.templatetags.static import static
from django.utils.html import format_html

register = template.Library()


@register.simple_tag
def icon(name):
    return format_html(
        '<svg class="icon" aria-hidden="true"><use href="{}#{}"></use></svg>',
        static("img/icons.svg"),
        name,
    )


@register.filter
def import_label(name):
    from django.core.exceptions import FieldDoesNotExist

    from customers.models import Customer
    from extensions.models import ExtensionPosition

    for model in [Customer, ExtensionPosition]:
        try:
            return str(model._meta.get_field(name).verbose_name)
        except FieldDoesNotExist:
            pass
    return str(name)


@register.filter
def import_status(value, field="status"):
    from django.utils.formats import localize

    from appointments.models import Appointment
    from extensions.models import ExtensionPosition

    choices = {
        "status": Appointment.Status.choices,
        "delivery_status": ExtensionPosition.Delivery.choices,
        "quantity_unit": ExtensionPosition.Unit.choices,
    }
    return dict(choices.get(field, [])).get(value, localize(value))
