"""Sync newsletter subscribers to an email service provider (ESP).

Pick one with ESP_PROVIDER = mailerlite | brevo | mailchimp (empty = no sync), plus ESP_API_KEY and
ESP_LIST_ID (MailerLite group id, Brevo list id, or Mailchimp audience id). Failures are logged and
stored on the subscriber; they never break signup. Retry with `python manage.py sync_subscribers`.
"""

import hashlib
import logging

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)
TIMEOUT = 6


class ESPError(Exception):
    pass


def _check(resp):
    if resp.status_code >= 400:
        raise ESPError(f"{resp.status_code}: {resp.text[:200]}")


def _mailerlite(email, subscribed):
    headers = {"Authorization": f"Bearer {settings.ESP_API_KEY}", "Accept": "application/json"}
    base = "https://connect.mailerlite.com/api/subscribers"
    if subscribed:
        payload = {"email": email, "status": "active"}
        if settings.ESP_LIST_ID:
            payload["groups"] = [settings.ESP_LIST_ID]
        _check(requests.post(base, json=payload, headers=headers, timeout=TIMEOUT))
    else:
        _check(requests.put(f"{base}/{email}", json={"status": "unsubscribed"}, headers=headers, timeout=TIMEOUT))


def _brevo(email, subscribed):
    headers = {"api-key": settings.ESP_API_KEY, "Accept": "application/json"}
    if subscribed:
        payload = {"email": email, "updateEnabled": True, "emailBlacklisted": False}
        if settings.ESP_LIST_ID:
            payload["listIds"] = [int(settings.ESP_LIST_ID)]
        _check(requests.post("https://api.brevo.com/v3/contacts", json=payload, headers=headers, timeout=TIMEOUT))
    else:
        _check(requests.put(f"https://api.brevo.com/v3/contacts/{email}", json={"emailBlacklisted": True},
                            headers=headers, timeout=TIMEOUT))


def _mailchimp(email, subscribed):
    key = settings.ESP_API_KEY
    dc = key.rsplit("-", 1)[-1]  # keys end with the datacenter, e.g. "...-us21"
    member = hashlib.md5(email.lower().encode()).hexdigest()  # noqa: S324 (Mailchimp's required id scheme)
    url = f"https://{dc}.api.mailchimp.com/3.0/lists/{settings.ESP_LIST_ID}/members/{member}"
    status = "subscribed" if subscribed else "unsubscribed"
    payload = {"email_address": email, "status_if_new": status, "status": status}
    _check(requests.put(url, json=payload, auth=("grckits", key), timeout=TIMEOUT))


PROVIDERS = {"mailerlite": _mailerlite, "brevo": _brevo, "mailchimp": _mailchimp}


def enabled():
    return settings.ESP_PROVIDER in PROVIDERS and bool(settings.ESP_API_KEY)


def sync(subscriber):
    """Push one subscriber's current state. Returns True on success."""
    if not enabled():
        return False
    try:
        PROVIDERS[settings.ESP_PROVIDER](subscriber.email, subscriber.is_active)
    except (requests.RequestException, ESPError) as exc:
        logger.warning("ESP sync failed for %s: %s", subscriber.email, exc)
        type(subscriber).objects.filter(pk=subscriber.pk).update(esp_error=str(exc)[:300])
        return False
    type(subscriber).objects.filter(pk=subscriber.pk).update(esp_synced_at=timezone.now(), esp_error="")
    return True
