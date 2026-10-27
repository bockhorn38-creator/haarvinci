import base64
import hashlib
import json
import secrets
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from . import provider
from .models import Device, Handoff


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def challenge(verifier):
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")


def response(payload, status=200):
    result = JsonResponse(payload, status=status)
    result["Cache-Control"] = "no-store"
    result["Referrer-Policy"] = "no-referrer"
    return result


def posted(request):
    if request.content_type != "application/json" or len(request.body) > 16000:
        raise ValueError
    return json.loads(request.body)


def cleanup():
    Handoff.objects.filter(expires_at__lt=timezone.now()).delete()


@csrf_exempt
@require_POST
def begin(request):
    cleanup()
    try:
        data = posted(request)
        role, mobile_challenge, device_key = data["role"], data["challenge"], data["device_key"]
        if (
            role not in ["business", "private"]
            or len(mobile_challenge) != 43
            or not 43 <= len(device_key) <= 128
        ):
            raise ValueError
        state, verifier = secrets.token_urlsafe(48), secrets.token_urlsafe(64)
        item = Handoff.objects.create(
            state_hash=digest(state),
            challenge=mobile_challenge,
            device_hash=digest(device_key),
            role=role,
            expires_at=timezone.now() + timedelta(minutes=10),
            encrypted_payload=provider.encrypt({"verifier": verifier}),
        )
        url = provider.authorization_url(role, verifier, state)
        return response({"id": str(item.pk), "authorization_url": url})
    except (ValueError, TypeError, ValidationError, KeyError):
        return response({"error": "invalid_request"}, 400)


@require_GET
def callback(request):
    cleanup()
    try:
        item = Handoff.objects.get(
            state_hash=digest(request.GET.get("state", "")),
            status="pending",
            expires_at__gt=timezone.now(),
        )
    except Handoff.DoesNotExist:
        return HttpResponse(
            "Diese Anmeldung ist abgelaufen oder bereits abgeschlossen.", status=400
        )
    if not Handoff.objects.filter(pk=item.pk, status="pending").update(status="processing"):
        return HttpResponse("Diese Anmeldung wird bereits verarbeitet.", status=409)
    if request.GET.get("error") or not request.GET.get("code"):
        item.status, item.encrypted_payload = "denied", ""
    else:
        try:
            verifier = provider.decrypt(item.encrypted_payload)["verifier"]
            token = provider.exchange(item.role, verifier, request.GET["code"])
            if not token.get("access_token") or not token.get("refresh_token"):
                raise ValueError
            item.status, item.encrypted_payload = "ready", provider.encrypt(token)
        except Exception:
            # Keine Google-Tokens, Codes oder Fehlertexte in Antworten/Logs übernehmen.
            item.status, item.encrypted_payload = "denied", ""
    item.save(update_fields=["status", "encrypted_payload"])
    result = HttpResponse(
        '<!doctype html><html lang="de"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Haarvinci – Google-Anmeldung</title><body style="font-family:system-ui;background:#f8f6f2;color:#5b283e;padding:32px"><h1>Google-Anmeldung beendet.</h1><p>Wechsle jetzt zurück zur Haarvinci-App. Dort wird die Verbindung geprüft und du kannst den Kalender auswählen.</p><p>Du kannst dieses Browserfenster schließen.</p></body></html>'
    )
    result["Cache-Control"], result["Referrer-Policy"] = "no-store", "no-referrer"
    result["Content-Security-Policy"] = (
        "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'"
    )
    return result


@csrf_exempt
@require_POST
@transaction.atomic
def finish(request):
    cleanup()
    try:
        data = posted(request)
        item = Handoff.objects.select_for_update().get(pk=data["id"], expires_at__gt=timezone.now())
        if not secrets.compare_digest(item.challenge, challenge(data["verifier"])):
            raise ValueError
        if item.status in ["pending", "processing"]:
            return response({"status": "pending"}, 202)
        if item.status != "ready":
            item.delete()
            return response({"error": "denied"}, 400)
        token = provider.decrypt(item.encrypted_payload)
        device = Device.objects.create(secret_hash=item.device_hash, role=item.role)
        item.delete()
        return response({"token": token, "device_id": str(device.pk)})
    except (ValueError, TypeError, ValidationError, KeyError, Handoff.DoesNotExist):
        return response({"error": "invalid_handoff"}, 400)


def authenticated_device(data):
    item = Device.objects.get(pk=data["device_id"])
    if not secrets.compare_digest(item.secret_hash, digest(data["device_key"])):
        raise ValueError
    return item


@csrf_exempt
@require_POST
def refresh(request):
    try:
        data = posted(request)
        device = authenticated_device(data)
        token = provider.refresh(device.role, data["refresh_token"])
        return response({"token": token})
    except (ValueError, TypeError, ValidationError, KeyError, Device.DoesNotExist):
        return response({"error": "invalid_device"}, 403)
    except Exception:
        return response({"error": "reauthorization_required"}, 401)


@csrf_exempt
@require_POST
def disconnect(request):
    try:
        device = authenticated_device(posted(request))
        device.delete()
        return response({"status": "disconnected"})
    except (ValueError, TypeError, ValidationError, KeyError, Device.DoesNotExist):
        return response({"error": "invalid_device"}, 403)
