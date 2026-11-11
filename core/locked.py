"""Full-version features shown as tasteful locked teasers."""

LOCKED_FEATURES = {
    "walkthrough_3d": ("3D / 360° walkthrough",
                       "Clients walk through their future home in 3D or 360° right in the browser or client portal.",
                       "Clients approve designs faster because they can see exactly what they are paying for."),
    "ar_view": ("AR “view in your room”",
                "Clients place a sofa, wardrobe or lamp in their own room using the phone camera.",
                "Removes doubt about size and colour before ordering."),
    "online_payments": ("Online payments (Razorpay)",
                        "Clients pay milestone invoices by UPI, card or net banking from the portal; receipts are automatic.",
                        "Get paid faster with less follow-up."),
    "inventory": ("Inventory & procurement",
                  "Purchase orders, stock, site deliveries and vendor bills linked to each project.",
                  "Know what was ordered, delivered and used — and stop material leakage."),
    "accounting": ("Advanced accounting & Tally export",
                   "Expense tracking, project profitability and one-click export to Tally.",
                   "See real profit per project and save hours for your accountant."),
    "team_payroll": ("Team attendance, payroll & contractors",
                     "Site attendance, salaries and contractor payments in one place.",
                     "Pay the right people the right amount, on time."),
    "whatsapp_api": ("WhatsApp Business API & marketing",
                     "Automatic WhatsApp confirmations, reminders and campaigns from your official business number.",
                     "Every client is updated without you typing a single message."),
    "roles_branches": ("Advanced roles & multi-branch",
                       "Custom permissions per role and multiple studios or branches under one login.",
                       "Grow the team without losing control."),
    "mobile_app": ("Mobile app for designers & supervisors",
                   "Android/iOS app to post site photos, mark tasks and record attendance from the site.",
                   "Site updates reach the client the moment work is done."),
    "ai_business": ("AI “Ask your business data”",
                    "Ask “How many leads did Instagram bring this month?” or “Which payments are overdue?”",
                    "Answers about your business in seconds, without reports."),
}


LOCKED_FEATURES.update({
    "lead_ads": ("Instagram & Facebook lead ads sync",
                 "Leads from your Instagram and Facebook ad forms land in the Leads board within seconds, tagged by campaign.",
                 "Reply first — the studio that calls back in 5 minutes usually wins the project."),
    "gcal_sync": ("Google Calendar two-way sync",
                  "Consultations and site visits sync both ways with each designer's Google Calendar.",
                  "No double bookings, and your team sees everything on their phones."),
    "email_campaigns": ("Email campaigns",
                        "Newsletters and festive offers to past clients and leads, with open and click tracking.",
                        "Past clients bring repeat work and referrals when you stay in touch."),
    "google_reviews": ("Automatic Google review requests",
                       "A polite WhatsApp/email asking happy clients for a Google review a week after handover.",
                       "More 5-star reviews means more enquiries from Google Maps."),
})


def _module_teasers():
    from .modules import MODULES
    benefits = {
        "website": "Turn Instagram and Google visitors into enquiries with your own premium website.",
        "cms": "Update projects and photos yourself — no developer needed.",
        "erp": "Every lead, project and payment in one place instead of WhatsApp and Excel.",
        "portal": "Faster approvals and fewer “what is the status?” calls.",
        "automation": "Clients stay informed without you typing every message.",
        "ai": "Answers enquiries 24×7, even when you are on site.",
    }
    return {"module_" + k: (label, what, benefits[k]) for k, label, _, what in MODULES}


LOCKED_FEATURES.update(_module_teasers())


def get(key):
    title, what, benefit = LOCKED_FEATURES[key]
    return {"key": key, "title": title, "what": what, "benefit": benefit}
