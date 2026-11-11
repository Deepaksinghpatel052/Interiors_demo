"""Offer modules for /why. Descriptions only — prices stay empty (fill them in the admin if you want them shown)."""
from website.models import Package

PACKAGES = [
    ("website", "Website", "globe2", "A premium, fast website that turns visitors into enquiries.",
     ["Home, portfolio, services, about, FAQ and contact pages", "Portfolio with before/after, mood boards and filters",
      "Style quiz, cost estimator and online booking", "WhatsApp button and enquiry forms on every page",
      "Mobile-first, SEO basics, your colours and logo"]),
    ("website-cms", "Website + CMS", "pencil-square", "Everything in Website, and you update it yourself.",
     ["Edit projects, photos, services, testimonials and FAQs", "Change homepage text, colours and contact details",
      "No developer needed for day-to-day changes"]),
    ("erp", "Studio ERP", "kanban", "Run leads, projects and money in one place.",
     ["Leads board and booking calendar", "Projects, tasks, design versions and site updates",
      "GST quotations and invoices with branded PDFs", "Payments, vendors and materials catalogue",
      "Client portal for approvals, documents and payments", "Owner dashboard"]),
    ("automation", "Automation", "lightning-charge", "Messages and reminders that go out on time.",
     ["Booking confirmations and consultation reminders", "“Quotation sent” and payment due reminders",
      "New-lead alerts and follow-up reminders", "Editable WhatsApp message templates and log"]),
    ("ai", "AI Assistant", "stars", "Answers enquiries 24×7 from your own studio knowledge.",
     ["Website assistant that captures leads", "Studio assistant for your team", "Knowledge base you control, with sources",
      "Chat logs and lead hand-off to WhatsApp or booking"]),
    ("complete", "Complete System", "gem", "Website + CMS, ERP, Automation and AI — one connected system.",
     ["Every module above, connected end to end", "One login for your team, one portal for clients",
      "Priority setup and training for your team"]),
]


def seed_packages(out):
    made = 0
    for order, (key, name, icon, tagline, items) in enumerate(PACKAGES):
        _, created = Package.objects.get_or_create(key=key, defaults={
            "name": name, "icon": icon, "tagline": tagline, "includes": "\n".join(items),
            "order": order, "is_bundle": key == "complete"})
        made += created
    out.write(f"  packages: {Package.objects.count()} (prices left empty)")
