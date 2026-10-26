from django.conf import settings
from django.utils import timezone


def brand(request):
    return {
        "is_demo": settings.DEBUG or getattr(settings, "DESKTOP_MODE", False),
        "desktop_mode": getattr(settings, "DESKTOP_MODE", False),
        "today": timezone.localdate(),
    }
