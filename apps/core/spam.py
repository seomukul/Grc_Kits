"""Lightweight spam protection without CAPTCHAs: honeypot field + minimum fill time + rate limit."""

import time

from django import forms
from django.core import signing
from django.core.cache import cache

MIN_SECONDS = 3
MAX_AGE = 60 * 60 * 6


class SpamProtectedForm(forms.Form):
    """Mix into a form. Render `{{ form.website }}` hidden and `{{ form.ts }}` as a hidden field."""

    website = forms.CharField(required=False, widget=forms.TextInput(attrs={
        "tabindex": "-1", "autocomplete": "off", "class": "hidden", "aria-hidden": "true",
    }))
    ts = forms.CharField(widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound:
            self.initial["ts"] = signing.dumps(time.time(), salt="form-ts")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("website"):
            raise forms.ValidationError("Spam detected.")
        try:
            started = signing.loads(self.data.get("ts", ""), salt="form-ts", max_age=MAX_AGE)
        except signing.BadSignature:
            raise forms.ValidationError("This form expired. Please reload the page and try again.")
        if time.time() - started < MIN_SECONDS:
            raise forms.ValidationError("That was quick! Please try again.")
        return cleaned


def rate_limited(key, limit=5, window=3600):
    """True if `key` has been used `limit` times within `window` seconds."""
    cache_key = f"rl:{key}"
    count = cache.get_or_set(cache_key, 0, window)
    if count >= limit:
        return True
    try:
        cache.incr(cache_key)
    except ValueError:
        cache.set(cache_key, 1, window)
    return False
