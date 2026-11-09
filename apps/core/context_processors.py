from django.conf import settings


def _tracking(s):
    cfg = {
        "ga4": s.ga4_measurement_id,
        "meta": s.meta_pixel_id,
        "linkedin": s.linkedin_partner_id,
    }
    return {k: v for k, v in cfg.items() if v} or None


def site(request):
    from .models import SiteSettings

    s = SiteSettings.load()
    return {
        "tracking_config": _tracking(s),
        "SITE_NAME": settings.SITE_NAME,
        "SITE_URL": settings.SITE_URL,
        "STRIPE_PUBLISHABLE_KEY": settings.STRIPE_PUBLISHABLE_KEY,
    }
