"""
Base settings shared by every environment.

Environment-specific overrides live in dev.py, prod.py and test.py.
All secrets and per-environment values come from environment variables (.env).
"""

from pathlib import Path

import environ
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    CSRF_TRUSTED_ORIGINS=(list, []),
)
environ.Env.read_env(BASE_DIR / ".env")

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env("CSRF_TRUSTED_ORIGINS")
SITE_URL = env("SITE_URL", default="http://localhost:8000").rstrip("/")
SITE_NAME = "GRCkits"

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
UNFOLD_APPS = [
    # Unfold must come before django.contrib.admin
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
]

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    "django.contrib.humanize",
]

THIRD_PARTY_APPS = [
    "django_htmx",
    "django_tailwind_cli",
]

LOCAL_APPS = [
    "apps.core",
    "apps.catalog",
    "apps.payments",
    "apps.orders",
    "apps.downloads",
    "apps.reviews",
    "apps.marketing",
    "apps.blog",
    "apps.services",
    "apps.pages",
    "apps.dashboard",
]

INSTALLED_APPS = UNFOLD_APPS + DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.site",
                "apps.pages.context_processors.footer_pages",
            ],
        },
    },
]

# ---------------------------------------------------------------------------
# Database (PostgreSQL)
# ---------------------------------------------------------------------------
DATABASES = {
    "default": env.db("DATABASE_URL", default="postgres://postgres:postgres@localhost:5432/grckits"),
}
DATABASES["default"]["ATOMIC_REQUESTS"] = True
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=60)
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "core.User"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard:home"
LOGOUT_REDIRECT_URL = "pages:home"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# I18N
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = env("TIME_ZONE", default="UTC")
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static & media
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "assets"]

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Paid product files are never served from MEDIA_URL. They live outside the
# public media root and are streamed by apps.downloads after an entitlement check.
PRIVATE_MEDIA_ROOT = env.path("PRIVATE_MEDIA_ROOT", default=BASE_DIR / "private_media")

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "private": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {"location": str(PRIVATE_MEDIA_ROOT), "base_url": None},
    },
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

# ---------------------------------------------------------------------------
# Tailwind v4 (django-tailwind-cli)
# ---------------------------------------------------------------------------
TAILWIND_CLI_SRC_CSS = "frontend/tailwind.css"
TAILWIND_CLI_DIST_CSS = "css/tailwind.css"
TAILWIND_CLI_VERSION = env("TAILWIND_CLI_VERSION", default="latest")

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="GRCkits <hello@grckits.com>")
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# ---------------------------------------------------------------------------
# Stripe
# ---------------------------------------------------------------------------
STRIPE_SECRET_KEY = env("STRIPE_SECRET_KEY", default="")
STRIPE_PUBLISHABLE_KEY = env("STRIPE_PUBLISHABLE_KEY", default="")
STRIPE_WEBHOOK_SECRET = env("STRIPE_WEBHOOK_SECRET", default="")
STRIPE_CURRENCY = env("STRIPE_CURRENCY", default="usd")

# ---------------------------------------------------------------------------
# Downloads
# ---------------------------------------------------------------------------
DOWNLOAD_LINK_MAX_USES = env.int("DOWNLOAD_LINK_MAX_USES", default=10)
DOWNLOAD_LINK_EXPIRY_DAYS = env.int("DOWNLOAD_LINK_EXPIRY_DAYS", default=365)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "{levelname} {asctime} {name} {message}", "style": "{"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "simple"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django": {"handlers": ["console"], "level": env("DJANGO_LOG_LEVEL", default="INFO"), "propagate": False},
        "apps": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}

# ---------------------------------------------------------------------------
# Unfold admin
# ---------------------------------------------------------------------------
UNFOLD = {
    "SITE_TITLE": "GRCkits Admin",
    "SITE_HEADER": "GRCkits",
    "SITE_SUBHEADER": "Store & content management",
    "SITE_URL": "/",
    "SITE_SYMBOL": "shield_lock",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "COLORS": {
        "primary": {
            "50": "oklch(97.7% .014 308.299)",
            "100": "oklch(94.6% .033 307.174)",
            "200": "oklch(90.2% .063 306.703)",
            "300": "oklch(82.7% .119 306.383)",
            "400": "oklch(71.4% .203 305.504)",
            "500": "oklch(62.7% .265 303.9)",
            "600": "oklch(55.8% .288 302.321)",
            "700": "oklch(49.6% .265 301.924)",
            "800": "oklch(43.8% .218 303.724)",
            "900": "oklch(38.1% .176 304.987)",
            "950": "oklch(29.1% .149 302.717)",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "title": _("Store"),
                "separator": True,
                "items": [
                    {"title": _("Products"), "icon": "inventory_2", "link": reverse_lazy("admin:catalog_product_changelist")},
                    {"title": _("Categories"), "icon": "category", "link": reverse_lazy("admin:catalog_category_changelist")},
                    {"title": _("Frameworks"), "icon": "verified", "link": reverse_lazy("admin:catalog_framework_changelist")},
                    {"title": _("Orders"), "icon": "receipt_long", "link": reverse_lazy("admin:orders_order_changelist")},
                    {"title": _("Download files"), "icon": "folder_zip", "link": reverse_lazy("admin:downloads_productfile_changelist")},
                    {"title": _("Reviews"), "icon": "reviews", "link": reverse_lazy("admin:reviews_review_changelist")},
                ],
            },
            {
                "title": _("Content"),
                "separator": True,
                "items": [
                    {"title": _("Blog posts"), "icon": "article", "link": reverse_lazy("admin:blog_post_changelist")},
                    {"title": _("Services"), "icon": "handshake", "link": reverse_lazy("admin:services_service_changelist")},
                    {"title": _("Service inquiries"), "icon": "mail", "link": reverse_lazy("admin:services_serviceinquiry_changelist")},
                    {"title": _("Pages"), "icon": "description", "link": reverse_lazy("admin:pages_page_changelist")},
                    {"title": _("Subscribers"), "icon": "campaign", "link": reverse_lazy("admin:marketing_subscriber_changelist")},
                ],
            },
            {
                "title": _("System"),
                "separator": True,
                "items": [
                    {"title": _("Users"), "icon": "person", "link": reverse_lazy("admin:core_user_changelist")},
                    {"title": _("Stripe events"), "icon": "webhook", "link": reverse_lazy("admin:payments_stripeevent_changelist")},
                ],
            },
        ],
    },
}
