from django.conf import settings
from django.utils import timezone


def brand(request):
    from appointments.models import CalendarConnection

    return {
        "is_demo": settings.DEBUG or getattr(settings, "DESKTOP_MODE", False),
        "desktop_mode": getattr(settings, "DESKTOP_MODE", False),
        "android_mode": getattr(settings, "ANDROID_MODE", False),
        "today": timezone.localdate(),
        "google_enabled": request.user.is_authenticated
        and CalendarConnection.objects.for_user(request.user).exclude(calendar_id="").exists(),
    }
