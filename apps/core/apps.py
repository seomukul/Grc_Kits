from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    label = "core"

    def ready(self):
        from django.db.models.signals import post_migrate

        from .roles import ensure_roles

        post_migrate.connect(ensure_roles, sender=self)
