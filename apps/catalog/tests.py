import importlib
from decimal import Decimal

from django.apps import apps as django_apps
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.catalog.models import Category, Product
from apps.catalog.views import LONG_DESCRIPTION_WORDS


def make(description="", **kw):
    cat, _ = Category.objects.get_or_create(slug="c", defaults={"name": "C"})
    return Product.objects.create(
        title="Kit", slug="kit", category=cat, price=Decimal("10"), short_description="Short",
        status="published", description=description, **kw,
    )


class LongDescriptionTests(TestCase):
    def test_short_description_renders_without_read_more(self):
        p = make("<h2>Overview</h2><p>Hello <strong>world</strong></p>")
        resp = self.client.get(p.get_absolute_url())
        self.assertContains(resp, "About this toolkit")
        self.assertContains(resp, '<h2 id="overview">Overview</h2>', html=False)
        self.assertNotContains(resp, "Read full description")

    def test_long_description_collapses(self):
        words = " ".join(["word"] * (LONG_DESCRIPTION_WORDS + 10))
        resp = self.client.get(make(f"<p>{words}</p>").get_absolute_url())
        self.assertContains(resp, "Read full description")
        self.assertContains(resp, "max-h-[28rem]")

    def test_empty_description_hides_section(self):
        self.assertNotContains(self.client.get(make("").get_absolute_url()), "About this toolkit")

    def test_render_strips_unsafe_html_even_if_stored(self):
        resp = self.client.get(make('<p>ok<script>alert(1)</script><img src=x onerror="alert(1)"></p>').get_absolute_url())
        body = resp.content.decode().split('id="description"')[1].split("</section>")[0]
        self.assertNotIn("<script", body)
        self.assertNotIn("onerror", body)

    @override_settings(ADMIN_2FA_REQUIRED=False)
    def test_admin_saves_sanitized_rich_text(self):
        owner = get_user_model().objects.create_superuser("o", "o@x.com", "pw")
        self.client.force_login(owner)
        p = make()
        self.assertContains(self.client.get(reverse("admin:catalog_product_change", args=[p.pk])), "prose-editor")
        data = {
            "title": "Kit", "slug": "kit", "category": p.category_id, "product_type": "excel", "status": "published",
            "short_description": "Short", "description": "<h2>Inside</h2><p>x</p><script>bad()</script>",
            "price": "10.00", "currency": "usd", "whats_included": "", "system_requirements": "",
            "cover_label": "", "preview_video_url": "", "meta_title": "", "meta_description": "",
        }
        for prefix in ("licenses", "images", "files", "faqs"):
            data.update({f"{prefix}-TOTAL_FORMS": 0, f"{prefix}-INITIAL_FORMS": 0})
        resp = self.client.post(reverse("admin:catalog_product_change", args=[p.pk]), data)
        self.assertEqual(resp.status_code, 302, getattr(resp, "context", None) and resp.context["adminform"].form.errors)
        p.refresh_from_db()
        self.assertIn("<h2>Inside</h2>", p.description)
        self.assertNotIn("<script", p.description)

    def test_migration_converts_plain_text(self):
        migration = importlib.import_module("apps.catalog.migrations.0005_alter_product_description_and_more")
        plain = make("Line one\n\nLine two")
        migration.plain_text_to_html(django_apps, None)
        plain.refresh_from_db()
        self.assertEqual(plain.description, "<p>Line one</p>\n\n<p>Line two</p>")
        migration.plain_text_to_html(django_apps, None)  # idempotent: already HTML
        plain.refresh_from_db()
        self.assertEqual(plain.description, "<p>Line one</p>\n\n<p>Line two</p>")
