from django.urls import path

from . import feeds, views

app_name = "blog"

urlpatterns = [
    path("", views.PostListView.as_view(), name="list"),
    path("feed/", feeds.LatestPostsFeed(), name="feed"),
    path("feed/atom/", feeds.AtomFeed(), name="feed_atom"),
    path("category/<slug:category>/", views.PostListView.as_view(), name="category"),
    path("tag/<slug:tag>/", views.PostListView.as_view(), name="tag"),
    path("<slug:slug>/", views.PostDetailView.as_view(), name="detail"),
]
