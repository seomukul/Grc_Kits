import stripe
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def get_client() -> stripe.StripeClient:
    if not settings.STRIPE_SECRET_KEY:
        raise ImproperlyConfigured("STRIPE_SECRET_KEY is not set.")
    return stripe.StripeClient(settings.STRIPE_SECRET_KEY)
