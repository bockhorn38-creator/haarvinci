import secrets

from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.shortcuts import redirect


class DesktopGateMiddleware:
    """Nur das eigene Programmfenster kennt den einmaligen Sitzungsschlüssel."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        supplied = request.headers.get("X-Haarvinci-Desktop", "")
        expected = settings.DESKTOP_TOKEN
        if not supplied or not secrets.compare_digest(supplied, expected):
            return HttpResponse(
                "Dieser Zugang ist nur im Haarvinci-Programm verfügbar.", status=403
            )
        if (
            request.path not in {"/einrichten/", "/bereit/"}
            and not request.path.startswith("/static/")
            and not get_user_model().objects.exists()
        ):
            return redirect("desktop_setup")
        return self.get_response(request)
