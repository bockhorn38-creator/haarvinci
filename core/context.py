from django.conf import settings
from django.utils import timezone


def brand(request):
    from appointments.models import DeviceCalendarConnection

    return {
        "is_demo": settings.DEBUG or getattr(settings, "DESKTOP_MODE", False),
        "desktop_mode": getattr(settings, "DESKTOP_MODE", False),
        "android_mode": getattr(settings, "ANDROID_MODE", False),
        "today": timezone.localdate(),
        "device_calendar_enabled": request.user.is_authenticated
        and DeviceCalendarConnection.objects.for_user(request.user)
        .exclude(state="disconnected")
        .exists(),
    }
