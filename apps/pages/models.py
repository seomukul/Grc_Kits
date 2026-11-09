from django.db import models
from django.urls import reverse

from apps.core.models import TimeStampedModel


class Page(TimeStampedModel):
    """Simple CMS page: about, terms, privacy, refund policy, etc."""

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    body = models.TextField(help_text="HTML allowed. Only staff can edit this.")
    is_published = models.BooleanField(default=True)
    show_in_footer = models.BooleanField(default=False)
    meta_description = models.CharField(max_length=160, blank=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("pages:page", args=[self.slug])


def lines(text):
    return [line.strip() for line in (text or "").splitlines() if line.strip()]


class HomeSection(models.Model):
    """One block of the home page. Admin can switch blocks on/off and reorder them."""

    class Key(models.TextChoices):
        HERO = "hero", "Hero slider"
        MARQUEE = "marquee", "Framework ticker"
        TRUST = "trust", "Trust bar"
        FEATURED = "featured", "Featured products"
        TOP_SELLING = "top_selling", "Top selling products"
        NEW_ARRIVALS = "new_arrivals", "New arrivals"
        BROWSE = "browse", "Browse by framework / category"
        BUNDLES = "bundles", "Bundles / best value"
        SERVICES = "services", "Services preview"
        TESTIMONIALS = "testimonials", "Testimonials"
        BLOG = "blog", "Latest from the blog"
        NEWSLETTER = "newsletter", "Newsletter signup"
        FAQ = "faq", "FAQ"
        COMPARE = "compare", "Toolkit vs consultant"
        STEPS = "steps", "How it works (steps)"
        INSIDE = "inside", "Inside every toolkit"
        AUTHOR = "author", "Written by practitioners"
        CTA = "cta", "Closing call to action"

    class Period(models.TextChoices):
        LAST_30 = "30d", "Last 30 days"
        ALL_TIME = "all", "All time"

    key = models.CharField(max_length=20, choices=Key.choices, unique=True)
    title = models.CharField(max_length=120, blank=True, help_text="Leave blank for the default heading.")
    subtitle = models.CharField(max_length=250, blank=True)
    is_enabled = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)
    item_limit = models.PositiveSmallIntegerField(default=6, help_text="Max items shown (products, posts…).")
    period = models.CharField(
        max_length=3, choices=Period.choices, default=Period.LAST_30, help_text="Top selling only."
    )
    eyebrow = models.CharField(max_length=60, blank=True, help_text="Small gold label above the heading.")
    content = models.TextField(
        blank=True,
        help_text=(
            "Text blocks for Steps / Inside / Compare: one per line as 'Title | text'. "
            "Compare: prefix lines with 'consultant:' or 'toolkit:'."
        ),
    )
    button_label = models.CharField(max_length=40, blank=True)
    button_url = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["order"]
        verbose_name = "home page section"

    def __str__(self):
        return self.get_key_display()

    @property
    def heading(self):
        return self.title or self.get_key_display()

    @property
    def blocks(self):
        """[(title, text), ...] parsed from `content`."""
        return [[p.strip() for p in (line.split("|", 1) + [""])[:2]] for line in lines(self.content)]

    def compare_rows(self, side):
        prefix = f"{side}:"
        return [line[len(prefix):].strip() for line in lines(self.content) if line.lower().startswith(prefix)]


class HeroSlide(models.Model):
    image = models.ImageField(upload_to="home/slides/", blank=True, help_text="Wide image, about 1600×700.")
    eyebrow = models.CharField(max_length=80, blank=True, help_text="Small text above the headline.")
    headline = models.CharField(max_length=120, help_text="Wrap words in *stars* to show them in gold.")
    subtext = models.CharField(max_length=250, blank=True)
    button_label = models.CharField(max_length=40, blank=True)
    button_url = models.CharField(max_length=300, blank=True, help_text="e.g. /kits/iso-27001-complete-toolkit/")
    secondary_label = models.CharField(max_length=40, blank=True)
    secondary_url = models.CharField(max_length=300, blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.headline


class TrustItem(models.Model):
    class Icon(models.TextChoices):
        DOWNLOAD = "download", "Download"
        EDIT = "edit", "Edit"
        BADGE = "badge", "Badge"
        LOCK = "lock", "Lock"
        REFRESH = "refresh", "Updates"
        GLOBE = "globe", "Globe"

    icon = models.CharField(max_length=20, choices=Icon.choices, default=Icon.BADGE)
    text = models.CharField(max_length=80)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.text


class Testimonial(TimeStampedModel):
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=150, blank=True, help_text="e.g. CISO, Acme Bank")
    quote = models.TextField()
    rating = models.PositiveSmallIntegerField(default=5)
    photo = models.ImageField(upload_to="testimonials/", blank=True)
    product = models.ForeignKey("catalog.Product", null=True, blank=True, on_delete=models.SET_NULL)
    is_active = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "-created_at"]

    def __str__(self):
        return f"{self.name}: {self.quote[:40]}"


class FAQItem(models.Model):
    class Topic(models.TextChoices):
        DELIVERY = "delivery", "Delivery"
        FORMATS = "formats", "File formats"
        LICENSING = "licensing", "Licensing"
        REFUNDS = "refunds", "Refunds"
        GENERAL = "general", "General"

    question = models.CharField(max_length=200)
    answer = models.TextField()
    topic = models.CharField(max_length=20, choices=Topic.choices, default=Topic.GENERAL)
    show_on_home = models.BooleanField(default=True)
    show_on_products = models.BooleanField(default=False, help_text="Also show under every product's FAQ.")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"

    def __str__(self):
        return self.question


class AboutProfile(models.Model):
    """Singleton for the About Me page."""

    name = models.CharField(max_length=100)
    headline = models.CharField(max_length=200, help_text="e.g. GRC consultant & ISO 27001 Lead Auditor")
    photo = models.ImageField(upload_to="about/", blank=True)
    bio = models.TextField(help_text="HTML allowed.")
    certifications = models.TextField(blank=True, help_text="One per line, e.g. CISA")
    experience = models.TextField(
        blank=True, help_text="One per line: 'Years | Role | Organisation', e.g. '2019–now | GRC Lead | Acme'."
    )
    stats = models.TextField(blank=True, help_text="One per line: 'Number | Label', e.g. '15+ | Years of experience'.")
    linkedin_url = models.URLField(blank=True)

    class Meta:
        verbose_name = verbose_name_plural = "about page"

    def __str__(self):
        return "About page"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        return cls.objects.filter(pk=1).first()

    @property
    def certification_list(self):
        return lines(self.certifications)

    @property
    def experience_rows(self):
        return [[p.strip() for p in (row.split("|") + ["", ""])[:3]] for row in lines(self.experience)]

    @property
    def stat_rows(self):
        return [[p.strip() for p in (row.split("|") + [""])[:2]] for row in lines(self.stats)]
