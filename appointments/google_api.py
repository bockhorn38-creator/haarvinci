"""Offizielle Calendar-v3-Endpunkte; keine automatische Weiterleitung von Bearer-Tokens."""

import json
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

API = "https://www.googleapis.com/calendar/v3"
SCOPES = {
    "business": [
        "https://www.googleapis.com/auth/calendar.calendarlist.readonly",
        "https://www.googleapis.com/auth/calendar.events.owned",
    ],
    "private": [
        "https://www.googleapis.com/auth/calendar.calendarlist.readonly",
        "https://www.googleapis.com/auth/calendar.events.freebusy",
    ],
}


class GoogleError(Exception):
    def __init__(self, code=0):
        self.code = code
        super().__init__("Google-Anfrage nicht abgeschlossen")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def request_json(url, *, method="GET", data=None, headers=None):
    body = json.dumps(data).encode() if data is not None else None
    request = Request(
        url,
        data=body,
        method=method,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            **(headers or {}),
        },
    )
    try:
        with build_opener(NoRedirect).open(request, timeout=25) as response:
            content = response.read(8 * 1024 * 1024 + 1)
            if len(content) > 8 * 1024 * 1024:
                raise GoogleError(413)
            return json.loads(content) if content else {}
    except HTTPError as error:
        # Keine Antworttexte loggen: Google-Fehler können Kalenderinhalte enthalten.
        raise GoogleError(error.code) from None
    except (URLError, OSError, ValueError) as error:
        raise GoogleError(0) from error


class GoogleCalendarAPI:
    def __init__(self, access_token, role):
        self.token, self.role = access_token, role

    def call(self, path, *, method="GET", data=None, etag=None, params=None):
        headers = {"Authorization": "Bearer " + self.token}
        if etag:
            headers["If-Match"] = etag
        url = API + path + ("?" + urlencode(params) if params else "")
        return request_json(url, method=method, data=data, headers=headers)

    def calendars(self):
        result, page = [], None
        for _ in range(100):
            data = self.call(
                "/users/me/calendarList",
                params={"maxResults": 250, **({"pageToken": page} if page else {})},
            )
            result.extend(
                item
                for item in data.get("items", [])
                if not item.get("deleted")
                and (self.role != "business" or item.get("accessRole") == "owner")
            )
            page = data.get("nextPageToken")
            if not page:
                return result
        raise GoogleError(413)

    def events(self, calendar_id, start, end):
        if self.role != "business":
            raise GoogleError(403)
        result, page, zone = [], None, "Europe/Berlin"
        for _ in range(100):
            data = self.call(
                "/calendars/" + quote(calendar_id, safe="") + "/events",
                params={
                    "timeMin": start.isoformat(),
                    "timeMax": end.isoformat(),
                    "singleEvents": "true",
                    "showDeleted": "true",
                    "maxResults": 2500,
                    **({"pageToken": page} if page else {}),
                },
            )
            result.extend(data.get("items", []))
            zone = data.get("timeZone", zone)
            page = data.get("nextPageToken")
            if not page:
                return result, zone
        raise GoogleError(413)

    def busy(self, calendar_id, start, end):
        return self.call(
            "/freeBusy",
            method="POST",
            data={
                "timeMin": start.isoformat(),
                "timeMax": end.isoformat(),
                "timeZone": "Europe/Berlin",
                "items": [{"id": calendar_id}],
            },
        )

    def event(self, calendar_id, event_id, *, method="GET", data=None, etag=None):
        if self.role != "business":
            raise GoogleError(403)
        return self.call(
            "/calendars/" + quote(calendar_id, safe="") + "/events/" + quote(event_id, safe=""),
            method=method,
            data=data,
            etag=etag,
            params={"sendUpdates": "none"} if method != "GET" else None,
        )

    def insert(self, calendar_id, data):
        if self.role != "business":
            raise GoogleError(403)
        return self.call(
            "/calendars/" + quote(calendar_id, safe="") + "/events",
            method="POST",
            data=data,
            params={"sendUpdates": "none"},
        )


def parse_instant(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise GoogleError(422)
    return parsed
