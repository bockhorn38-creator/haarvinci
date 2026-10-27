import secrets

from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.shortcuts import redirect

GATE_COOKIE = "haarvinci_android_gate"


class AndroidGateMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = request.COOKIES.get(GATE_COOKIE, "")
        if not token or not secrets.compare_digest(token, settings.DESKTOP_TOKEN):
            return HttpResponse("Dieser Zugang ist nur in Haarvinci verfügbar.", status=403)
        if (
            request.path not in {"/einrichten/", "/bereit/"}
            and not request.path.startswith("/static/")
            and not get_user_model().objects.exists()
        ):
            return redirect("desktop_setup")
        return self.get_response(request)
