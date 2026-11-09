from django.views.generic import DetailView, ListView

from .models import Post


class PostListView(ListView):
    template_name = "blog/post_list.html"
    context_object_name = "posts"
    paginate_by = 10

    def get_queryset(self):
        return Post.objects.published().select_related("author")


class PostDetailView(DetailView):
    template_name = "blog/post_detail.html"
    context_object_name = "post"

    def get_queryset(self):
        return Post.objects.published().select_related("author").prefetch_related("related_products")
