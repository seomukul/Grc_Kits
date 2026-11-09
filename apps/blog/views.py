from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.views.generic import DetailView, ListView

from apps.marketing.forms import SubscribeForm

from .models import BlogCategory, Post, Tag
from .rendering import render_body

TOC_MIN_HEADINGS = 3


class PostListView(ListView):
    template_name = "blog/post_list.html"
    context_object_name = "posts"
    paginate_by = 9

    def get_queryset(self):
        qs = Post.objects.published().select_related("author", "category")
        self.category = self.tag = None
        if slug := self.kwargs.get("category"):
            self.category = get_object_or_404(BlogCategory, slug=slug)
            qs = qs.filter(category_id__in=self.category.descendant_ids())
        if slug := self.kwargs.get("tag"):
            self.tag = get_object_or_404(Tag, slug=slug)
            qs = qs.filter(tags=self.tag)
        self.q = self.request.GET.get("q", "").strip()
        page = self.request.GET.get("page", "1")
        self.featured = None
        if not (self.category or self.tag or self.q) and page in ("", "1"):
            self.featured = qs.filter(is_featured=True).first()
            if self.featured:
                qs = qs.exclude(pk=self.featured.pk)
        if self.q:
            qs = qs.filter(Q(title__icontains=self.q) | Q(excerpt__icontains=self.q) | Q(body__icontains=self.q))
        return qs

    def get_template_names(self):
        if self.request.htmx and not self.request.htmx.boosted:
            return ["blog/_post_grid.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        live = Q(posts__status__in=["published", "scheduled"])
        ctx.update(
            category=self.category,
            tag=self.tag,
            q=self.q,
            categories=BlogCategory.objects.filter(parent__isnull=True)
            .annotate(n=Count("posts", filter=live)).prefetch_related("children"),
            featured=self.featured,
        )
        return ctx


class PostDetailView(DetailView):
    template_name = "blog/post_detail.html"
    context_object_name = "post"

    def get_queryset(self):
        qs = Post.objects.select_related("author", "category", "related_service").prefetch_related(
            "tags", "related_products__category", "related_products__frameworks", "attachments"
        )
        # Staff can preview drafts and scheduled posts.
        return qs if self.request.user.is_staff else qs.published()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        post = self.object
        body = render_body(post.body)
        tag_ids = list(post.tags.values_list("pk", flat=True))
        related = (
            Post.objects.published().exclude(pk=post.pk)
            .filter(Q(category=post.category) | Q(tags__in=tag_ids)).distinct()
            .select_related("category")[:3]
        )
        ctx.update(
            body=body.html,
            toc=body.toc if len(body.toc) >= TOC_MIN_HEADINGS else [],
            related_posts=related,
            products=list(post.related_products.all()),
            subscribe_form=SubscribeForm(),
            share_url=self.request.build_absolute_uri(post.get_absolute_url()),
        )
        return ctx
