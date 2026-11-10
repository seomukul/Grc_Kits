from datetime import time

from django.db import migrations


def defaults(apps, schema_editor):
    """Sunday–Thursday, 10:00–17:00 Asia/Dhaka (Bangladesh work week). Edit in Admin → Booking settings."""
    Settings = apps.get_model("bookings", "BookingSettings")
    Rule = apps.get_model("bookings", "AvailabilityRule")
    settings, created = Settings.objects.get_or_create(pk=1)
    if created or not Rule.objects.exists():
        for weekday in (6, 0, 1, 2, 3):  # Sun, Mon, Tue, Wed, Thu
            Rule.objects.create(settings=settings, weekday=weekday, start_time=time(10), end_time=time(17))


class Migration(migrations.Migration):
    dependencies = [("bookings", "0001_initial")]
    operations = [migrations.RunPython(defaults, migrations.RunPython.noop)]
