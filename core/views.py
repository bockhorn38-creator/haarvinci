import json
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET

from customers.models import Customer


@login_required
def dashboard(request):
    customers = Customer.objects.for_user(request.user)
    now = timezone.localdate()
    return render(
        request,
        "core/dashboard.html",
        {
            "nav": "dashboard",
            "customer_count": customers.count(),
            "new_count": customers.filter(created_at__date__gte=now.replace(day=1)).count(),
            "notes_count": customers.exclude(notes="").count(),
            "recent_customers": customers.order_by("-created_at")[:4],
        },
    )


@login_required
def account(request):
    return render(request, "core/account.html", {"nav": "account"})


@require_GET
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return JsonResponse({"status": "ok"})
    except Exception:
        return JsonResponse({"status": "unavailable"}, status=503)


@require_GET
def manifest(request):
    return HttpResponse(
        json.dumps(
            {
                "name": "Haarvinci · Connys Kundenbuch",
                "short_name": "Haarvinci",
                "lang": "de",
                "start_url": "/",
                "scope": "/",
                "display": "standalone",
                "background_color": "#f8f5f1",
                "theme_color": "#5b283e",
                "icons": [
                    {
                        "src": "/static/img/icon-192.png",
                        "sizes": "192x192",
                        "type": "image/png",
                        "purpose": "any",
                    },
                    {
                        "src": "/static/img/icon-512.png",
                        "sizes": "512x512",
                        "type": "image/png",
                        "purpose": "any maskable",
                    },
                ],
            }
        ),
        content_type="application/manifest+json",
    )


@require_GET
def service_worker(request):
    response = HttpResponse(
        (Path(settings.BASE_DIR) / "static/js/sw.js").read_text(),
        content_type="application/javascript",
    )
    response["Service-Worker-Allowed"] = "/"
    return response
