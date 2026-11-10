import math
import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags
from django_prose_editor.fields import ProseEditorField

from apps.core.models import TimeStampedModel
from apps.core.richtext import RICH_TEXT

# Editor features + sanitization rules live in apps/core/richtext.py (shared with products).
BODY_EDITOR = RICH_TEXT


class BlogCategory(TimeStampedModel):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children",
        help_text="Optional: makes this a sub-category.",
    )
    description = models.TextField(blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "blog category"
        verbose_name_plural = "blog categories"

    def __str__(self):
        return f"{self.parent} › {self.name}" if self.parent_id else self.name

    def clean(self):
        node, seen = self.parent, {self.pk}
        while node is not None:
            if node.pk in seen:
                raise ValidationError({"parent": "A category can't be its own ancestor."})
            seen.add(node.pk)
            node = node.parent

    def get_absolute_url(self):
        return reverse("blog:category", args=[self.slug])

    def descendant_ids(self):
        ids, frontier = [self.pk], [self.pk]
        while frontier:
            frontier = list(BlogCategory.objects.filter(parent_id__in=frontier).values_list("pk", flat=True))
            ids += frontier
        return ids


class Tag(models.Model):
    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("blog:tag", args=[self.slug])


class PostQuerySet(models.QuerySet):
    def published(self):
        """Published posts, plus scheduled ones whose time has come."""
        return self.filter(
            status__in=[Post.Status.PUBLISHED, Post.Status.SCHEDULED], published_at__lte=timezone.now()
        )


class Post(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SCHEDULED = "scheduled", "Scheduled"
        PUBLISHED = "published", "Published"

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=220)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="posts",
        help_text="Defaults to you.",
    )
    category = models.ForeignKey(BlogCategory, null=True, blank=True, on_delete=models.SET_NULL, related_name="posts")
    tags = models.ManyToManyField(Tag, blank=True, related_name="posts")
    excerpt = models.CharField(max_length=300, blank=True)
    body = ProseEditorField(
        config=BODY_EDITOR,
        sanitize=True,
        help_text="Paste a YouTube or Vimeo link on its own line to embed the video.",
    )
    cover_image = models.ImageField("featured image", upload_to="blog/", blank=True)
    frameworks = models.ManyToManyField("catalog.Framework", blank=True, related_name="posts")
    related_products = models.ManyToManyField(
        "catalog.Product", blank=True, related_name="posts",
        help_text="Shown as a call-to-action box inside the post and in the sidebar.",
    )
    related_service = models.ForeignKey(
        "services.Service", null=True, blank=True, on_delete=models.SET_NULL, related_name="posts",
        help_text="Optional consulting CTA at the end of the post.",
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT, db_index=True)
    published_at = models.DateTimeField(
        null=True, blank=True, help_text="For Scheduled posts: when the post goes live."
    )
    is_featured = models.BooleanField(default=False)

    meta_title = models.CharField(max_length=70, blank=True)
    meta_description = models.CharField(max_length=160, blank=True)
    canonical_url = models.URLField(blank=True, help_text="Only if this post was first published elsewhere.")
    og_image = models.ImageField("social share image", upload_to="blog/og/", blank=True)

    objects = PostQuerySet.as_manager()

    class Meta:
        ordering = ["-published_at", "-created_at"]

    def __str__(self):
        return self.title

    def clean(self):
        if self.status == self.Status.SCHEDULED and not self.published_at:
            raise ValidationError({"published_at": "Pick a date and time for scheduled posts."})

    def save(self, *args, **kwargs):
        if self.status == self.Status.PUBLISHED and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("blog:detail", args=[self.slug])

    @property
    def is_live(self):
        return self.status != self.Status.DRAFT and self.published_at and self.published_at <= timezone.now()

    @property
    def word_count(self):
        return len(re.findall(r"\w+", strip_tags(self.body or "")))

    @property
    def reading_minutes(self):
        return max(1, math.ceil(self.word_count / 220))

    @property
    def summary(self):
        if self.excerpt:
            return self.excerpt
        text = strip_tags(self.body or "").strip()
        return (text[:197] + "…") if len(text) > 200 else text


class PostAttachment(models.Model):
    """Downloadable files offered inside a post (e.g. a free checklist)."""

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="attachments")
    title = models.CharField(max_length=150)
    file = models.FileField(upload_to="blog/attachments/")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


class MediaAsset(TimeStampedModel):
    """Image library for the blog editor: upload here, then paste the URL into the editor's image button."""

    title = models.CharField(max_length=150)
    file = models.ImageField(upload_to="blog/media/")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "media image"

    def __str__(self):
        return self.title
