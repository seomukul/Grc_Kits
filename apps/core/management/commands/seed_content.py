"""Editorial starter content: services (from cyberprolab.com, expanded), home page, FAQs, legal drafts.

Safe to run in production and more than once: it only creates missing records and never
overwrites anything edited in the admin.

    python manage.py seed_content
"""

from django.core.management.base import BaseCommand

from apps.pages.models import FAQItem, HeroSlide, Page, TrustItem
from apps.services.models import Service, ServiceFAQ

SERVICES = [
    {
        "slug": "isms-iso-27001",
        "title": "Information Security Management System (ISMS)",
        "icon": "shield",
        "summary": "Design, implement and certify an ISO/IEC 27001 ISMS that protects the confidentiality, integrity and availability of your information.",
        "description": (
            "An Information Security Management System (ISMS) is a structured approach to protecting sensitive "
            "information from unauthorized access, disclosure or modification. It brings together the policies, "
            "procedures and controls that keep your information confidential, accurate and available.\n\n"
            "We help you build an ISMS that fits how your organization actually works, not a shelf of documents. "
            "From scoping and risk assessment to internal audit and certification support, we guide your team "
            "through every clause of ISO/IEC 27001 and the Annex A controls."
        ),
        "deliverables": [
            "ISMS scope, context and interested-parties analysis",
            "Information security policy and full policy set",
            "Risk assessment methodology and risk register",
            "Statement of Applicability (SoA)",
            "Risk treatment plan and control implementation roadmap",
            "Internal audit and management review",
            "Certification audit readiness support",
        ],
        "process": [
            ("Gap assessment", "We compare your current practices against ISO/IEC 27001 and Annex A."),
            ("Scope & risk", "Define the ISMS scope, assess risks and agree on treatment."),
            ("Implement", "Roll out policies, procedures and controls with your team."),
            ("Audit & improve", "Run an internal audit and management review, then fix findings."),
            ("Certify", "Support you through Stage 1 and Stage 2 certification audits."),
        ],
        "audience": ["Startups selling to enterprises", "Banks & financial institutions", "SaaS & IT service providers", "Organizations preparing for certification"],
        "faqs": [
            ("How long does ISO 27001 implementation take?", "Most organizations are audit-ready in 3–9 months, depending on size, scope and how much already exists."),
            ("Do you issue the certificate?", "No. Certification is issued by an accredited certification body. We prepare you and support you during their audit."),
            ("Can we use your templates instead?", "Yes. Our ISO 27001 toolkits cover the documentation; this service adds hands-on implementation and audit support."),
        ],
        "cta": "Request a quote",
    },
    {
        "slug": "vapt",
        "title": "Vulnerability Assessment & Penetration Testing (VAPT)",
        "icon": "bug",
        "summary": "Find and fix exploitable weaknesses in your networks, applications and people before attackers do.",
        "description": (
            "We offer comprehensive vulnerability assessments, analysis and penetration testing, with actionable, "
            "risk-ranked remediation and tailored phishing simulations to identify and mitigate threats.\n\n"
            "Our testers combine automated scanning with manual exploitation to show you real business impact, "
            "not just a list of CVEs. Every finding comes with clear evidence, a severity rating and practical "
            "remediation steps, followed by a free retest."
        ),
        "deliverables": [
            "External and internal network penetration testing",
            "Web application and API testing (OWASP Top 10)",
            "Mobile application testing",
            "Phishing and social-engineering simulations",
            "Executive summary and detailed technical report",
            "Risk-ranked remediation plan",
            "Retest to confirm fixes",
        ],
        "process": [
            ("Scoping", "Agree targets, rules of engagement and testing windows."),
            ("Discovery", "Map the attack surface and identify vulnerabilities."),
            ("Exploitation", "Safely validate which weaknesses are exploitable and their impact."),
            ("Reporting", "Deliver executive and technical reports with remediation guidance."),
            ("Retest", "Verify your fixes and issue an updated report."),
        ],
        "audience": ["Regulated organizations (banks, fintech, healthcare)", "SaaS and e-commerce platforms", "Companies preparing for PCI DSS, ISO 27001 or SOC 2"],
        "faqs": [
            ("Will testing disrupt our systems?", "We agree rules of engagement and testing windows in advance and avoid destructive techniques on production."),
            ("How often should we test?", "At least annually and after significant changes. PCI DSS and many regulators require regular testing."),
        ],
        "cta": "Request a VAPT quote",
    },
    {
        "slug": "is-audit",
        "title": "IS Audit",
        "icon": "audit",
        "summary": "Independent information systems audits that strengthen IT governance and demonstrate compliance.",
        "description": (
            "We enhance IT governance and compliance with expert IS audit services: audit planning, risk-based "
            "auditing, controls assessment and compliance reporting.\n\n"
            "Led by CISA-certified auditors, our audits follow recognized frameworks and give management, boards "
            "and regulators an objective view of how well your IT controls are designed and operating."
        ),
        "deliverables": [
            "Risk-based IS audit plan",
            "IT general controls (ITGC) review",
            "Access management, change management and operations testing",
            "Regulatory compliance assessment (e.g. Bangladesh Bank ICT guidelines)",
            "Audit report with findings, ratings and recommendations",
            "Management action plan follow-up",
        ],
        "process": [
            ("Plan", "Understand your environment and build a risk-based audit plan."),
            ("Fieldwork", "Interview owners, inspect evidence and test controls."),
            ("Report", "Share draft findings, agree management responses, issue the final report."),
            ("Follow up", "Verify that agreed actions have been completed."),
        ],
        "audience": ["Banks and financial institutions", "Internal audit departments needing IT expertise", "Organizations facing regulatory IT audits"],
        "faqs": [
            ("Can you act as our outsourced IT internal audit function?", "Yes. We can run your annual IS audit plan or co-source specific audits with your internal audit team."),
        ],
        "cta": "Request an audit",
    },
    {
        "slug": "grc",
        "title": "Governance, Risk & Compliance (GRC)",
        "icon": "scale",
        "summary": "Meet regulatory requirements, manage risk and maintain strong governance frameworks.",
        "description": (
            "We help organizations meet regulatory requirements, manage risk and maintain strong governance "
            "frameworks.\n\n"
            "Whether you're mapping controls across ISO 27001, NIST CSF, PCI DSS and local regulations or "
            "building a compliance program from scratch, we design a practical GRC operating model with clear "
            "ownership, policies and evidence your auditors will accept."
        ),
        "deliverables": [
            "Regulatory and framework gap analysis",
            "Unified control framework and control mapping",
            "Policy and procedure development",
            "Compliance calendar and evidence tracker",
            "Board and management reporting",
            "Virtual CISO / compliance advisory (retainer)",
        ],
        "process": [
            ("Assess", "Identify obligations and compare them with current controls."),
            ("Design", "Build the control framework, policies and ownership model."),
            ("Operate", "Embed monitoring, evidence collection and reporting."),
            ("Improve", "Review regularly and adapt to new regulations."),
        ],
        "audience": ["Organizations juggling multiple frameworks", "Growing companies without an in-house GRC team", "Boards needing clear risk and compliance reporting"],
        "faqs": [
            ("Which frameworks do you cover?", "ISO 27001, ISO 42001, NIST CSF, PCI DSS, SOC 2, Bangladesh Bank guidelines (BB CSF) and more."),
        ],
        "cta": "Talk to a GRC expert",
    },
    {
        "slug": "risk-management",
        "title": "Risk Management",
        "icon": "risk",
        "summary": "Identify, assess and mitigate threats to operations with actionable, business-focused insight.",
        "description": (
            "Our risk management services help organizations identify, assess and mitigate threats to operations. "
            "We provide actionable insights to strengthen security, ensure compliance and build a resilient, "
            "risk-aware organization.\n\n"
            "We set up a risk methodology your leadership understands, run workshops with the people who own the "
            "risks, and leave you with a living risk register and treatment plan."
        ),
        "deliverables": [
            "Risk management framework and methodology (ISO 31000 / ISO 27005 aligned)",
            "Risk appetite and tolerance statements",
            "Facilitated risk assessment workshops",
            "Enterprise / IT risk register",
            "Risk treatment plans and KRIs",
            "Third-party / vendor risk assessment",
        ],
        "process": [
            ("Context", "Understand objectives, assets and risk appetite."),
            ("Identify & analyse", "Run workshops to identify and rate risks."),
            ("Treat", "Agree controls, owners and deadlines."),
            ("Monitor", "Track KRIs and review the register regularly."),
        ],
        "audience": ["Leadership teams and boards", "Risk and compliance functions", "Organizations preparing for ISO 27001 or regulatory reviews"],
        "faqs": [
            ("Do you provide a risk register template?", "Yes. Our risk register is also sold as a standalone Excel toolkit, and we customise it during the engagement."),
        ],
        "cta": "Request a quote",
    },
    {
        "slug": "cyber-security-training",
        "title": "Cyber Security Training",
        "icon": "training",
        "summary": "Hands-on cybersecurity training and certification prep that builds a security-first workforce.",
        "description": (
            "We empower organizations through IT training and awareness programs, with cybersecurity workshops, "
            "simulation training and best practices that strengthen workforce skills.\n\n"
            "Our expert-led sessions combine hands-on labs, simulations and real-world scenarios. Training is "
            "available in person, virtually or in a hybrid format to fit your team's schedule."
        ),
        "deliverables": [
            "Certified Information Systems Auditor (CISA)",
            "Certified Information Security Manager (CISM)",
            "Certified Information Systems Security Professional (CISSP)",
            "Certified Ethical Hacker (CEH)",
            "CompTIA Security+",
            "ISO/IEC 27001 Lead Implementer",
            "ISO/IEC 27001 Lead Auditor",
            "Security awareness & phishing simulation programs",
        ],
        "process": [
            ("Training needs analysis", "Agree goals, audience and format."),
            ("Delivery", "Expert-led sessions with labs and practical exercises."),
            ("Assessment", "Quizzes, mock exams or simulations to measure progress."),
            ("Follow-up", "Reports, certificates of attendance and refresher plans."),
        ],
        "audience": ["IT and security teams", "Auditors and risk professionals", "All staff (awareness training)"],
        "faqs": [
            ("Is the exam fee included?", "Usually not. Exam vouchers are issued by ISACA, ISC2, EC-Council, CompTIA or the certification body; we can quote them separately."),
            ("Do you run private in-house sessions?", "Yes. We tailor content and schedule for your organization, in person or online."),
        ],
        "cta": "Request training",
    },
]

HERO_SLIDES = [
    {
        "eyebrow": "Built by a practicing GRC professional",
        "headline": "Audit-ready GRC templates & toolkits",
        "subtext": "Policies, risk registers, checklists and dashboards for ISO 27001, ISO 42001, NIST, PCI DSS and BB CSF. Download, customise, pass your audit.",
        "button_label": "Browse kits", "button_url": "/kits/",
        "secondary_label": "Get expert help", "secondary_url": "/services/",
    },
    {
        "eyebrow": "Best value",
        "headline": "Complete ISO 27001 toolkit",
        "subtext": "Every policy, register and template you need for certification, bundled at a discount.",
        "button_label": "See the bundle", "button_url": "/kits/?type=bundle",
    },
    {
        "eyebrow": "Consulting",
        "headline": "Need hands-on help? Our certified team can implement it with you.",
        "subtext": "ISMS, VAPT, IS audit, risk management and training.",
        "button_label": "Book a consultation", "button_url": "/contact/",
    },
]

TRUST = [
    ("download", "Instant download"),
    ("edit", "Fully editable files"),
    ("badge", "Built by a practicing GRC professional"),
    ("lock", "Secure payment via Stripe"),
]

FAQS = [
    ("delivery", "How do I receive my files?", "Right after payment you'll see download buttons on the confirmation page, and we email you the links. You can re-download any time from My Library by signing in with your purchase email."),
    ("formats", "What file formats do you use?", "Templates come as editable Microsoft Word (.docx) and Excel (.xlsx) files, with some checklists in PDF. Bundles are delivered as ZIP files."),
    ("licensing", "Can I use the templates for my whole team?", "A Single-user license covers one person. Choose a Team license (up to 10 users in one organization) or an Organization license (unlimited users in one legal entity) at checkout. Resale or redistribution isn't allowed."),
    ("general", "Do I get updates?", "Yes. When we release a new version of a kit you bought, we email you a fresh download link at no extra cost."),
    ("refunds", "What is your refund policy?", "Because files are delivered instantly, we generally can't refund digital products once downloaded. If a file is faulty or not as described, contact us within 14 days and we'll fix it or refund you."),
    ("general", "Will these templates guarantee certification?", "No template can guarantee certification, but ours are written by a practicing auditor and follow the standards closely. You'll still need to tailor them to your organization."),
]

LICENSE_TERMS = """<p><em>Draft. Please have this reviewed by your lawyer before launch.</em></p>
<h2>1. What you're buying</h2>
<p>When you buy a GRCkits product you receive a non-exclusive, non-transferable license to use and modify the files for your organization's internal purposes. You don't buy ownership of the templates; GRCkits keeps all copyright.</p>
<h2>2. License tiers</h2>
<ul>
<li><strong>Single user:</strong> one named individual may use the files.</li>
<li><strong>Team:</strong> up to 10 users within one organization.</li>
<li><strong>Organization:</strong> unlimited users within one legal entity (not its parent, subsidiaries or clients).</li>
</ul>
<h2>3. Consultants</h2>
<p>Consultants may use the files to deliver work to a client, provided a separate license is purchased for each client organization that receives the documents.</p>
<h2>4. What's not allowed</h2>
<ul>
<li>Reselling, sublicensing, sharing or redistributing the files, in original or modified form, as templates or products.</li>
<li>Publishing the files or substantial parts of them online.</li>
<li>Removing copyright notices from unmodified files.</li>
</ul>
<h2>5. Updates</h2>
<p>Your license includes free updates to the product you purchased for as long as we maintain it.</p>
<h2>6. No warranty</h2>
<p>The templates are provided as guidance. They must be tailored to your organization and don't guarantee compliance or certification.</p>
"""

REFUND_POLICY = """<p><em>Draft. Please have this reviewed before launch.</em></p>
<p>Our products are digital downloads delivered instantly, so we generally can't offer refunds once the files have been downloaded.</p>
<p>We will gladly fix the problem or refund you in full if, within <strong>14 days</strong> of purchase:</p>
<ul>
<li>a file is corrupted or won't open and we can't provide a working copy, or</li>
<li>the product is materially different from its description.</li>
</ul>
<p>Contact us with your order number. Refunded orders lose access to downloads.</p>
<p>Consulting services are governed by the terms in your proposal or contract.</p>
"""


class Command(BaseCommand):
    help = "Create starter site content (services, home page, FAQs, legal drafts) without overwriting edits."

    def handle(self, *args, **options):
        created = 0
        for order, data in enumerate(SERVICES):
            service, is_new = Service.objects.get_or_create(
                slug=data["slug"],
                defaults={
                    "title": data["title"],
                    "icon": data["icon"],
                    "summary": data["summary"],
                    "description": data["description"],
                    "deliverables": "\n".join(data["deliverables"]),
                    "process_steps": "\n".join(f"{t} | {d}" for t, d in data["process"]),
                    "audience": "\n".join(data["audience"]),
                    "cta_label": data["cta"],
                    "order": order,
                },
            )
            if is_new:
                created += 1
                for i, (q, a) in enumerate(data["faqs"]):
                    ServiceFAQ.objects.create(service=service, question=q, answer=a, order=i)

        if not HeroSlide.objects.exists():
            for i, slide in enumerate(HERO_SLIDES):
                HeroSlide.objects.create(order=i, **slide)
                created += 1
        if not TrustItem.objects.exists():
            for i, (icon, text) in enumerate(TRUST):
                TrustItem.objects.create(icon=icon, text=text, order=i)
                created += 1
        if not FAQItem.objects.exists():
            for i, (topic, q, a) in enumerate(FAQS):
                FAQItem.objects.create(topic=topic, question=q, answer=a, order=i, show_on_products=topic in ("delivery", "licensing"))
                created += 1

        for slug, title, body in [("license", "License Terms", LICENSE_TERMS), ("refunds", "Refund Policy", REFUND_POLICY)]:
            page, is_new = Page.objects.get_or_create(slug=slug, defaults={"title": title, "body": body, "show_in_footer": True})
            if not is_new and "content goes here" in page.body:  # replace seed_demo placeholder only
                page.body = body
                page.save(update_fields=["body"])
            created += is_new

        self.stdout.write(self.style.SUCCESS(f"Site content ready ({created} new records)."))
