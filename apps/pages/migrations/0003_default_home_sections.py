from django.db import migrations

DEFAULTS = [
    ("hero", ""), ("trust", ""), ("featured", "Featured toolkits"), ("browse", "Browse by framework"),
    ("top_selling", "Top selling"), ("new_arrivals", "New arrivals"), ("bundles", "Bundles & best value"),
    ("services", "Need expert help?"), ("testimonials", "What customers say"), ("blog", "From the blog"),
    ("newsletter", ""), ("faq", "Frequently asked questions"),
]


def create_sections(apps, schema_editor):
    HomeSection = apps.get_model("pages", "HomeSection")
    for order, (key, title) in enumerate(DEFAULTS):
        HomeSection.objects.get_or_create(key=key, defaults={"title": title, "order": order * 10})


class Migration(migrations.Migration):
    dependencies = [("pages", "0002_aboutprofile_faqitem_heroslide_homesection_trustitem_and_more")]
    operations = [migrations.RunPython(create_sections, migrations.RunPython.noop)]
