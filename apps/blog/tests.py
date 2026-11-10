import warnings
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.blog.models import BlogCategory, Post, Tag
from apps.blog.rendering import render_body
from apps.core.roles import ensure_roles

warnings.filterwarnings("ignore", module="django_prose_editor")
User = get_user_model()

BODY = (
    "<p>Intro</p><h2>First</h2><p>a</p><h3>Sub</h3><p>b</p><h2>Second</h2>"
    "<p><a href=\"https://youtu.be/abcdefghijk\">https://youtu.be/abcdefghijk</a></p>"
)


def post(title, **kw):
    kw.setdefault("status", Post.Status.PUBLISHED)
    kw.setdefault("body", BODY)
    return Post.objects.create(title=title, slug=title.lower().replace(" ", "-"), **kw)


class BlogTests(TestCase):
    def setUp(self):
        self.parent = BlogCategory.objects.create(name="ISO", slug="iso")
        self.child = BlogCategory.objects.create(name="ISO 27001", slug="iso-27001", parent=self.parent)
        self.tag = Tag.objects.create(name="Audit", slug="audit")

    def test_status_visibility_and_staff_preview(self):
        live = post("Live")
        draft = post("Draft", status=Post.Status.DRAFT)
        future = post("Future", status=Post.Status.SCHEDULED, published_at=timezone.now() + timedelta(days=1))
        past = post("Due", status=Post.Status.SCHEDULED, published_at=timezone.now() - timedelta(minutes=1))
        listing = self.client.get(reverse("blog:list")).content.decode()
        self.assertIn(live.title, listing)
        self.assertIn(past.title, listing)
        self.assertNotIn(future.title, listing)
        self.assertNotIn(">Draft<", listing)
        self.assertEqual(self.client.get(draft.get_absolute_url()).status_code, 404)
        staff = User.objects.create_user("s", "s@x.com", "pw", is_staff=True)
        self.client.force_login(staff)
        resp = self.client.get(draft.get_absolute_url())
        self.assertContains(resp, "Preview")
        self.assertContains(resp, 'name="robots" content="noindex"')

    def test_category_includes_subcategories_tag_and_search(self):
        a = post("Child post", category=self.child)
        b = post("Other post")
        b.tags.add(self.tag)
        cat = self.client.get(reverse("blog:category", args=["iso"])).content.decode()
        self.assertIn(a.title, cat)
        self.assertNotIn(b.title, cat)
        self.assertContains(self.client.get(reverse("blog:tag", args=["audit"])), b.title)
        resp = self.client.get(reverse("blog:list"), {"q": "child"}, HTTP_HX_REQUEST="true")
        self.assertTemplateUsed(resp, "blog/_post_grid.html")
        self.assertContains(resp, a.title)
        self.assertNotContains(resp, b.title)

    def test_detail_toc_embed_reading_time_related(self):
        p = post("Guide", category=self.child)
        post("Sibling", category=self.child)
        resp = self.client.get(p.get_absolute_url())
        self.assertContains(resp, 'id="first"')
        self.assertContains(resp, 'href="#sub"')
        self.assertContains(resp, "youtube-nocookie.com/embed/abcdefghijk")
        self.assertContains(resp, "1 min read")
        self.assertContains(resp, "Sibling")

    def test_render_sanitizes_dangerous_html(self):
        html = render_body('<p onclick="x()">t<script>alert(1)</script></p><img src=x onerror=alert(1)>'
                           '<a href="javascript:alert(1)">l</a><iframe src="https://evil"></iframe>').html
        for bad in ("<script", "onerror", "onclick", "javascript:", "evil"):
            self.assertNotIn(bad, html)

    def test_admin_form_sanitizes_on_save(self):
        owner = User.objects.create_superuser("o", "o@x.com", "pw")
        self.client.force_login(owner)
        with override_settings(ADMIN_2FA_REQUIRED=False):
            self.client.post(reverse("admin:blog_post_add"), {
                "title": "Saved", "slug": "saved", "status": "draft", "excerpt": "",
                "body": "<p>ok</p><script>alert(1)</script>",
                "attachments-TOTAL_FORMS": 0, "attachments-INITIAL_FORMS": 0,
            })
        self.assertNotIn("<script", Post.objects.get(slug="saved").body)

    def test_editor_can_write_posts(self):
        editor = User.objects.create_user("ed", "e@x.com", "pw", is_staff=True)
        editor.groups.add(ensure_roles())
        self.client.force_login(editor)
        with override_settings(ADMIN_2FA_REQUIRED=False):
            self.assertEqual(self.client.get(reverse("admin:blog_blogcategory_add")).status_code, 200)
            self.assertEqual(self.client.get(reverse("admin:blog_mediaasset_add")).status_code, 200)

    def test_rss_and_sitemap(self):
        post("Feed item", excerpt="Summary here")
        rss = self.client.get(reverse("blog:feed"))
        self.assertEqual(rss.status_code, 200)
        self.assertContains(rss, "Feed item")
        self.assertEqual(self.client.get(reverse("blog:feed_atom")).status_code, 200)
        self.assertContains(self.client.get("/sitemap.xml"), "/blog/category/iso/")

    def test_category_cycle_rejected(self):
        from django.core.exceptions import ValidationError

        self.parent.parent = self.child
        with self.assertRaises(ValidationError):
            self.parent.full_clean()


class AdminEditorStylesTests(TestCase):
    @override_settings(ADMIN_2FA_REQUIRED=False)
    def test_admin_loads_editor_stylesheet(self):
        self.client.force_login(User.objects.create_superuser("o2", "o2@x.com", "pw"))
        resp = self.client.get(reverse("admin:blog_post_add"))
        self.assertContains(resp, "css/admin.css")
        self.assertContains(resp, "prose-editor")
