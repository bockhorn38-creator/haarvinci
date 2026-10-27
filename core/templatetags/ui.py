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
def import_status(value):
    from appointments.models import Appointment
    from extensions.models import ExtensionPosition

    return dict(
        Appointment.Status.choices
        + ExtensionPosition.Delivery.choices
        + ExtensionPosition.Unit.choices
    ).get(value, value)
