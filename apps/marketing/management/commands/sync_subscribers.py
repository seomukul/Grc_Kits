from django.core.management.base import BaseCommand, CommandError

from apps.marketing import esp
from apps.marketing.models import Subscriber


class Command(BaseCommand):
    help = "Push subscribers to the configured email tool (MailerLite, Brevo or Mailchimp)."

    def add_arguments(self, parser):
        parser.add_argument("--all", action="store_true", help="Resync everyone, not just failed/unsynced ones.")

    def handle(self, *args, **options):
        if not esp.enabled():
            raise CommandError("Set ESP_PROVIDER and ESP_API_KEY first.")
        qs = Subscriber.objects.all() if options["all"] else Subscriber.objects.filter(esp_synced_at__isnull=True)
        ok = sum(esp.sync(s) for s in qs.iterator())
        self.stdout.write(self.style.SUCCESS(f"Synced {ok} of {qs.count()} subscribers."))
