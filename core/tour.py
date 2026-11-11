"""Guided demo tour: the whole sales story, one benefit per step. Rendered as JSON for static/js/tour.js."""
from django.urls import reverse


def steps(studio=None):
    r = reverse
    from django.conf import settings
    home = r("website:home") if settings.LANDING_PAGE else "/"
    all_steps = [
        {"role": "visitor", "url": home, "el": ".hero h1",
         "title": "1 · A visitor finds the studio",
         "text": "Your own fast, mobile-first website with your projects, services and a WhatsApp button on every page.",
         "benefit": "More enquiries from Instagram and Google — not just likes."},
        {"role": "visitor", "url": r("website:portfolio"), "el": ".filter-bar .filter-group",
         "title": "2 · Explores your portfolio",
         "text": "Real projects by room, style and budget, with before/after sliders and mood boards.",
         "benefit": "A professional presentation that builds trust before the first call."},
        {"role": "visitor", "url": r("website:quiz"), "el": "#quizForm",
         "title": "3 · Takes the style quiz",
         "text": "Six quick questions reveal their style and suggest matching projects — and capture their details.",
         "benefit": "Warm leads who already know what they like."},
        {"role": "visitor", "url": home, "el": ".chat-launcher", "open_chat": True, "module": "ai",
         "title": "4 · Asks the AI assistant",
         "text": "It answers from your own services, FAQs and projects, 24×7 — and hands over to WhatsApp or a booking.",
         "benefit": "No enquiry waits until morning."},
        {"role": "visitor", "url": r("bookings:book"), "el": "#bookingForm",
         "title": "5 · Books a consultation",
         "text": "Live slots from your calendar, no double bookings, and an instant confirmation with a calendar invite.",
         "benefit": "Time saved on back-and-forth calls."},
        {"role": "owner", "url": r("studio:leads"), "el": "#leadBoard",
         "title": "6 · You see the lead and the booking",
         "text": "Every enquiry lands on one board, tagged by source. Drag cards as the conversation moves forward.",
         "benefit": "Nothing forgotten in WhatsApp chats."},
        {"role": "owner", "url": r("automations:index"), "el": ".wa-preview", "module": "automation",
         "title": "7 · Messages are written for you",
         "text": "Confirmations, reminders and payment nudges are prepared from your templates — one tap to send.",
         "benefit": "Clients stay informed without you typing."},
        {"role": "owner", "url": r("finance:quotations"), "el": ".erp-content .panel, .erp-content",
         "title": "8 · Build a quotation in minutes",
         "text": "Room-wise items from your catalogue, GST split automatically, payment schedule and a branded PDF.",
         "benefit": "Professional quotes the same day — not next week."},
        {"role": "client", "url": r("portal:designs"), "el": ".design-teaser", "module": "portal",
         "title": "9 · The client approves a design",
         "text": "Designs, comments and approvals in one private portal — with a clear record of what was approved.",
         "benefit": "Faster approvals and fewer disputes later."},
        {"role": "owner", "url": r("finance:invoices"), "el": ".kpi",
         "title": "10 · Payment recorded",
         "text": "Milestone invoices, part payments and balances, with reminders for anything due.",
         "benefit": "Know exactly who owes what, always."},
        {"role": "owner", "url": r("studio:dashboard"), "el": ".kpi",
         "title": "11 · Your dashboard updates",
         "text": "Leads, conversions, projects and money in one view — on your phone or laptop.",
         "benefit": "Run the studio on facts, not guesswork."},
        {"role": "visitor", "url": r("website:why"), "el": "main h1",
         "title": "That’s the full journey",
         "text": "Pick only the modules you need today — website, ERP, automation or AI — and add more later.",
         "benefit": "Start small, grow into the complete system."},
    ]
    out = []
    for step in all_steps:
        module = step.pop("module", None)
        if studio is None or module is None or getattr(studio, "module_" + module, True):
            out.append(step)
    return out
