from django.db import migrations

# New sections for the redesign + the new default order. Existing titles are kept if edited.
LAYOUT = [
    ("hero", 0, {}),
    ("marquee", 10, {}),
    ("browse", 20, {"eyebrow": "Disciplines", "title": "Browse by discipline",
                    "subtitle": "Every toolkit sits in one practice area, so you can go straight to the standards you're working on."}),
    ("featured", 30, {"eyebrow": "The library", "title": "Featured toolkits"}),
    ("compare", 40, {
        "eyebrow": "Why a toolkit", "title": "The toolkit vs. the consultant",
        "subtitle": "Same expertise, a fraction of the time and budget.",
        "content": "\n".join([
            "consultant: Day rates that add up quickly over a multi-week engagement",
            "consultant: Weeks of drafting before the first policy arrives",
            "consultant: Every change outside the scope becomes another invoice",
            "consultant: Progress depends on someone else's calendar",
            "toolkit: One-time price with instant download",
            "toolkit: Start the same day: add your logo, adapt, approve",
            "toolkit: Most of the drafting already done, fully editable forever",
            "toolkit: Written and maintained by a practicing GRC auditor",
        ]),
        "button_label": "Not sure which kit you need? Ask us", "button_url": "/contact/",
    }),
    ("bundles", 50, {"eyebrow": "Best value", "title": "Complete toolkits & bundles"}),
    ("steps", 60, {
        "eyebrow": "How it works", "title": "From checkout to audit-ready in three steps",
        "content": "\n".join([
            "Choose your framework | Pick the standard or regulation you need, or ask us and we'll point you to the right kit.",
            "Download instantly | Pay securely with Stripe and get every Word and Excel file the moment checkout completes.",
            "Adapt and pass | Add your logo, tailor the guidance text to your organization, and walk into your audit prepared.",
        ]),
    }),
    ("inside", 70, {
        "eyebrow": "What you get", "title": "Inside every toolkit",
        "subtitle": "A consistent, professionally formatted document set with ownership, version control and review cycles built in.",
        "content": "\n".join([
            "Policies & procedures | Clause-by-clause coverage with guidance on what to tailor.",
            "Registers & logs | Risk, asset, incident and supplier registers ready to use.",
            "Risk assessment templates | Methodology, scoring criteria and treatment plans.",
            "Audit checklists | Internal audit programs mapped to every requirement.",
            "RACI & roles | Clear ownership so nothing falls between teams.",
            "KPI dashboards | Excel dashboards to report status to management.",
            "Latest revisions | Updated when standards change, with free updates for buyers.",
            "No locked files | Plain Word and Excel you can edit, rebrand and keep.",
        ]),
    }),
    ("top_selling", 75, {"eyebrow": "Popular", "title": "Top selling"}),
    ("new_arrivals", 78, {"eyebrow": "Just released", "title": "New arrivals"}),
    ("author", 80, {"eyebrow": "The author", "title": "Written by a working GRC practitioner",
                    "button_label": "More about me", "button_url": "/about/"}),
    ("testimonials", 85, {"eyebrow": "Reviews", "title": "What customers say"}),
    ("trust", 88, {}),
    ("services", 90, {"eyebrow": "Consulting", "title": "Need hands-on help?"}),
    ("blog", 95, {"eyebrow": "Insights", "title": "From the blog"}),
    ("faq", 100, {"eyebrow": "Questions", "title": "Frequently asked questions"}),
    ("newsletter", 105, {}),
    ("cta", 110, {"title": "Be audit-ready by tomorrow morning",
                  "subtitle": "Download a complete, editable toolkit today and spend your time adapting, not drafting.",
                  "button_label": "Browse all toolkits", "button_url": "/kits/"}),
]


def apply(apps, schema_editor):
    HomeSection = apps.get_model("pages", "HomeSection")
    old_titles = {"Featured toolkits", "Browse by framework", "Top selling", "New arrivals", "Bundles & best value",
                  "Need expert help?", "What customers say", "From the blog", "Frequently asked questions", ""}
    for key, order, defaults in LAYOUT:
        obj, created = HomeSection.objects.get_or_create(key=key, defaults={"order": order, **defaults})
        if created:
            continue
        obj.order = order
        for field, value in defaults.items():
            current = getattr(obj, field)
            if field != "title" and not current or field == "title" and current in old_titles:
                setattr(obj, field, value)
        obj.save()


class Migration(migrations.Migration):
    dependencies = [("pages", "0004_homesection_button_label_homesection_button_url_and_more")]
    operations = [migrations.RunPython(apply, migrations.RunPython.noop)]
