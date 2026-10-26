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
