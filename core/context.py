from django.conf import settings
from django.utils import timezone


def brand(request):
    return {"is_demo": settings.DEBUG, "today": timezone.localdate()}
