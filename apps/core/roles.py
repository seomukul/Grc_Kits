"""Staff roles. Owner = superuser. Editor = staff in the 'Editor' group: blog only."""

from django.contrib.auth.models import Group, Permission

EDITOR = "Editor"
EDITOR_APPS = ["blog"]


def ensure_roles(**kwargs):
    group, _ = Group.objects.get_or_create(name=EDITOR)
    perms = Permission.objects.filter(content_type__app_label__in=EDITOR_APPS)
    group.permissions.set(perms)
    return group
