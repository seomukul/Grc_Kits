"""Passwordless sign-in for customers: a one-time link emailed to them.

The link signs "<user pk>:<last_login timestamp>". Logging in updates last_login, so a link
works only once. It also expires after MAX_AGE.
"""

from django.contrib.auth import get_user_model
from django.core import signing

SALT = "grckits.magic-login"
MAX_AGE = 20 * 60  # seconds


def _login_stamp(user):
    return str(int(user.last_login.timestamp())) if user.last_login else "0"


def make_token(user):
    return signing.TimestampSigner(salt=SALT).sign(f"{user.pk}:{_login_stamp(user)}")


def user_from_token(token):
    """Return the user for a valid, unused token, otherwise None."""
    try:
        value = signing.TimestampSigner(salt=SALT).unsign(token, max_age=MAX_AGE)
    except signing.BadSignature:
        return None
    pk, stamp = value.split(":", 1)
    user = get_user_model().objects.filter(pk=pk, is_active=True).first()
    if user is None or _login_stamp(user) != stamp:
        return None
    return user
