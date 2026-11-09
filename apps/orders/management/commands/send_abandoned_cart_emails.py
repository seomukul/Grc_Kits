from django.core.management.base import BaseCommand

from apps.orders.abandoned import send_reminders


class Command(BaseCommand):
    help = "Send one reminder to people who started checkout but didn't pay (run hourly from cron)."

    def handle(self, *args, **options):
        self.stdout.write(f"Sent {send_reminders()} reminder(s).")
