from django.db import models
from django.utils.formats import date_format, localize


def display_value(field, raw):
    if raw is None or raw == "":
        return ""
    if field.choices:
        return str(dict(field.flatchoices).get(raw, raw))
    value = field.to_python(raw)
    if isinstance(field, models.DateField):
        return date_format(value, "d.m.Y")
    return str(localize(value))
