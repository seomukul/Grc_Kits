from django.db import migrations

# From the Missouri Certificate of Organization (filed 2 November 2026).
DETAILS = {
    "legal_name": "GRC Kits LLC",
    "registration": "Missouri limited liability company, No. LC014795326",
    "business_address": "117 S Lexington Street, Ste 100\nHarrisonville, MO 64701\nUnited States",
    "governing_law": "the State of Missouri, USA",
}


def apply(apps, schema_editor):
    """Fill the business details on new installs (production). Never overwrite values already edited in admin."""
    SiteSettings = apps.get_model("core", "SiteSettings")
    s, _ = SiteSettings.objects.get_or_create(pk=1)
    changed = False
    for field, value in DETAILS.items():
        current = getattr(s, field)
        if not current or (field == "legal_name" and current == "GRCkits"):
            setattr(s, field, value)
            changed = True
    if changed:
        s.save()


class Migration(migrations.Migration):
    dependencies = [("core", "0007_sitesettings_business_address_and_more")]
    operations = [migrations.RunPython(apply, migrations.RunPython.noop)]
