from django.core.management.base import BaseCommand

from apps.orders.customers import rebuild_all


class Command(BaseCommand):
    help = "Rebuild the Customers table from orders."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS(f"Rebuilt {rebuild_all()} customers."))
