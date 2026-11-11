# Modules and packages

Use this to prepare quotations. Every module is switched on/off in **Studio settings → Modules** — one codebase,
sold as a small package or the complete system. Prices are intentionally not in this file or in the demo
(`Package` records in the admin have an empty price field; fill it only if you want prices shown on `/why`).

## Built and working in the demo

### 1. Website
Home, portfolio (filters by room/style/budget, case studies with gallery, before/after slider, mood board),
services, about, FAQ, contact with map, privacy, photo credits; style quiz; cost estimator (ranges from
per-sq-ft rates in settings); online consultation booking with live slots, blocked dates, `.ics` invite;
WhatsApp buttons everywhere; mobile-first; SEO basics (titles, descriptions, Open Graph); white-label colours/logo.

### 2. Website + CMS
Everything in Website, plus **Studio → Website content**: homepage/about text, portfolio projects (details, cover,
multi-photo upload with automatic resizing, before/after pairs, mood-board rooms and swatches), services,
testimonials (with “Sample” flag) and FAQs. Brand, contact and availability in Studio settings.

### 3. Studio ERP
- **Sales:** leads Kanban (drag between stages, sources, follow-up dates, notes, WhatsApp/call buttons), lead → project
  conversion (creates client login + milestones), bookings calendar (drag to reschedule, status).
- **Delivery:** projects board, project workspace (overview, tasks, design versions, site updates, documents, billing),
  task list per person, milestones.
- **Money:** GST quotation builder (rooms, catalogue items, discounts, CGST/SGST or IGST, round-off, versions/revisions,
  branded PDF with amount in words), payment schedule, invoices with Indian FY numbering, part payments
  (UPI/bank/cash/cheque), outstanding/overdue.
- **Purchasing:** vendors, materials catalogue with HSN/SAC and GST %.
- **Reports:** leads by source and conversion, revenue by month, outstanding with ageing, CSV exports.
- **Team & roles (basic):** Owner and Team Member; add/deactivate logins.

### 4. Client portal
Project overview and progress, design versions with approve / request changes / comments, timeline, site
updates with photos, documents (secure download), quotation/invoice PDFs, payments, requests/snags (become tasks).
Live alerts to the studio when the client acts.

### 5. Automation
Booking confirmation, consultation reminder (1 day before), “quotation sent”, payment due reminder, new-lead alert
to the owner, follow-up for leads untouched 3 days. Editable templates, on/off per automation, log with one-tap
“Send via WhatsApp” (wa.me). Daily checks via `run_automations` (cron) or button. **Messages are prepared, not
auto-sent** in this version.

### 6. AI assistant
Website Design Assistant (public, captures leads, hands over to WhatsApp/booking) and Studio Assistant (internal
documents too). Retrieval-augmented: answers only from the knowledge base with citations; offline mode needs no
API key; Claude when `ANTHROPIC_API_KEY` is set. Knowledge base editor (text/PDF), test panel, chat logs.
Rate-limited and sanitised.

### Complete System
All six modules, connected end to end.

## Locked in the demo (full version — quote separately)

| Feature | Module it extends |
|---|---|
| 3D / 360° walkthrough viewer | Website / Portal |
| AR “view in your room” | Website / Portal |
| Online payments (Razorpay: UPI, cards, net banking) with automatic receipts | Portal + ERP |
| Inventory & procurement (POs, stock, site deliveries, vendor bills) | ERP |
| Advanced accounting, expense tracking, Tally export, project profitability | ERP |
| Team attendance, payroll, contractor payments | ERP |
| WhatsApp Business API auto-send & marketing campaigns | Automation |
| Instagram / Facebook lead ads sync | Automation |
| Google Calendar two-way sync | Automation |
| Email campaigns | Automation |
| Automatic Google review requests | Automation |
| Advanced roles & permissions, multi-branch | ERP |
| Mobile app for designers & site supervisors | ERP |
| AI “Ask your business data” | AI |

Technical approach for each: `FULL_VERSION_ROADMAP.md`.

## Suggested package combinations

| Package | Modules | Typical buyer |
|---|---|---|
| Website | Website | New studio, mostly Instagram enquiries |
| Website + CMS | Website, CMS | Studio that posts new projects often |
| Studio ERP | ERP (+ Portal recommended) | Busy studio drowning in WhatsApp and Excel |
| Automation | Automation (needs ERP data) | Studio with many bookings / payment follow-ups |
| AI Assistant | AI (+ Website) | Studio getting many repeat questions |
| Complete System | All | Growing studio with a team |

Hosting, domain, SMS/WhatsApp API charges and Anthropic API usage are pass-through costs — mention them in the quote.
