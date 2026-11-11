# Interior Studio — Sales Demo (Django)

A white-label business system for Indian interior design studios: website, client portal, studio ERP,
automation and an AI assistant. Demo brand: **Aangan Interiors**. Built by DEVNIXPLUS.

> Status: **Phases 1–8 complete** — website, showcase tools, estimator and booking; Studio ERP with GST
> quotations, invoices, payments, vendors and reports; client portal; Website CMS; automations; AI assistants (RAG);
> guided tour, `/why` sales page; `reset_demo`, `brand_demo` and `setup_client`; module switches. See `docs/PLAN.md`.
>
> More docs: `docs/DEMO_SCRIPT.md` (10-minute sales call) · `docs/MODULES_AND_PACKAGES.md` (for quotations) ·
> `docs/FULL_VERSION_ROADMAP.md` (locked features) · `docs/NEW_CLIENT_SETUP.md` (launch checklist).

## Setup (Windows, inside the project venv)

```powershell
py -3.12 -m venv venv                         # already created
.\venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env                        # then set SECRET_KEY, DEVNIX_WHATSAPP
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py seed_demo
.\venv\Scripts\python.exe manage.py runserver
```

Open http://127.0.0.1:8000/ (use `runserver 8010` if port 8000 is taken by another project).

macOS/Linux: use `python3 -m venv venv` and `venv/bin/python` instead.

## Run on a server with Docker

The app runs in Docker on port `APP_PORT` (9005) behind the server's own nginx, at https://interiors.devnixplus.com:
`docker compose --env-file .env_server up -d --build`. Server settings: `.env_server`; nginx config:
`deploy/nginx/interiors.devnixplus.com.conf`. Full steps: **docs/DOCKER_DEPLOY.md**.

## Demo logins

| Role | Username | Password |
|---|---|---|
| Owner | `owner` | `demo12345` |
| Team member | `designer` | `demo12345` |
| Client | `client` | `demo12345` |
| Superuser (Django admin at `/admin/`) | `admin` | `admin12345` |

## Rebrand the demo for a prospect (2 minutes)

```powershell
.\venv\Scripts\python.exe manage.py brand_demo --name "Sharma Interiors" --city "Gwalior" --phone "9826012345" `
    --logo C:\prospects\sharma\logo.png --images C:\prospects\sharma\photos\
```

- Changes the name, legal name, city, phone/WhatsApp, e-mail (or `--email`), logo, and picks the **colours from the
  logo** (or pass `--color "#1A73E8"`). Grey/black logos keep the default blue.
- Replaces the old name and city in the website text, services, FAQs, projects, AI knowledge base and messages.
- `--images` puts the prospect's own photos (JPG/PNG/WebP, resized automatically) on the portfolio covers and
  galleries, 4 per project (`--per-project`). Optional: `--address`, `--instagram`, `--tagline`, `--whatsapp`.
- Then fine-tune in **Studio → Website content** and **Studio settings**. To go back: `reset_demo --full`.

## Reset the demo (nightly)

```powershell
.\venv\Scripts\python.exe manage.py reset_demo            # keeps the current branding and modules
.\venv\Scripts\python.exe manage.py reset_demo --full     # also back to Aangan Interiors defaults
```

Deletes everything prospects created (leads, bookings, projects, quotations, invoices, chats, uploads, extra
logins, edited message templates) and seeds fresh data (~2 minutes). It refuses to run when `DEMO_MODE=False`.
Schedule it nightly: Windows Task Scheduler →
`C:\path\venv\Scripts\python.exe C:\path\manage.py reset_demo --offline`, or cron
`30 2 * * * cd /srv/demo && venv/bin/python manage.py reset_demo --offline`.

## Turn the demo into a client's live system

```powershell
.\venv\Scripts\python.exe manage.py setup_client --owner-username rohit --owner-name "Rohit Sharma" --keep-content
```

Removes demo data and demo logins (`admin`, `owner`, `designer`, `client`), keeps Studio settings, creates the
owner login (a strong password is generated and shown once unless `--password` is given), and writes
`DEMO_MODE=False` to `.env`. `--keep-content` keeps the portfolio/services/FAQs/knowledge base (use after
`brand_demo` with their photos; sample testimonials are always removed); `--keep-catalogue` keeps vendors and
materials. Full checklist: `docs/NEW_CLIENT_SETUP.md`.

## Modules (sell small or complete packages)

**Studio settings → Modules**: Website, Website CMS, Client portal, Studio ERP, Automation, AI assistant.
A switched-off module disappears from menus and its pages return a clean “not part of this package” page.
With *Show locked teasers* on, switched-off modules (and full-version features) appear as locked items that open
the “I want this feature” modal; switch it off to hide them completely. Without the ERP, the studio opens on
Website content; without the website, `/` goes to the login page.

## Tests

```powershell
.\venv\Scripts\python.exe manage.py test
```

## Useful commands

| Command | What it does |
|---|---|
| `reset_demo [--full] [--offline]` | Wipe demo data and re-seed (nightly) |
| `brand_demo --name … [--city --phone --logo --images …]` | Rebrand the demo for a prospect |
| `setup_client --owner-username …` | Turn the demo into a fresh client instance |
| `seed_demo` | Creates studio settings, users, services, FAQs, sample testimonials and 10 portfolio projects with generated images |
| `seed_demo --flush` | Deletes demo content (website, leads, bookings) and seeds again |
| `seed_demo --offline` | Seeds without downloading photos (generated illustrations are used instead) |
| `run_automations` | Daily automation checks (consultation reminders, payment due, lead follow-ups) — logged, not sent |
| `fetch_demo_photos` | Downloads the curated CC0 interior photos (~8 MB) and applies them to the portfolio, services, designs and site updates — keeps leads, bookings and projects |

## Photos and theme

- Demo photos are real, royalty-free **CC0** interior photographs (Rawpixel and StockSnap, found via Openverse).
  The list with credits is `core/demo_photos.json`; credits are shown on `/photo-credits/`.
  No images from real designers' websites are used. For a prospect, replace them with their own project photos.
- Theme: premium **white + blue + black**. Three colours in **Admin → Studio settings** drive the whole look:
  *Primary colour* (`#0081F6`), *Secondary colour* (`#2474F8`, used in gradients and hovers) and
  *Dark colour* (`#111212`, text, dark sections, footer and studio sidebar). Backgrounds are white.

## Public demo URLs

| Page | URL |
|---|---|
| Sample studio website home (Aangan Interiors) | `/` |
| Product landing page (DEVNIXPLUS) — only when `LANDING_PAGE=True` in `.env` (studio home then moves to `/demo/`) | `/` |
| Portfolio + case study | `/portfolio/`, `/portfolio/<slug>/` |
| Mood board | `/moodboard/<slug>/` |
| Style quiz | `/style-quiz/` |
| Cost estimator | `/estimate/` |
| Book a consultation | `/book/` |
| Why this system (demo mode) | `/why/` |

## Studio ERP (owner dashboard)

Open `/studio/` and sign in as `owner` (or use **View as → Designer-owner** in the demo ribbon).

| Page | URL | Who |
|---|---|---|
| Dashboard (KPIs, today, overdue, charts) | `/studio/` | Owner, team |
| Leads Kanban (drag between stages) | `/studio/leads/` | Owner, team |
| Bookings calendar (drag to reschedule) | `/studio/bookings/` | Owner, team |
| Weekly availability & blocked dates | `/studio/bookings/availability/` | Owner |
| Projects board/list, project detail | `/studio/projects/` | Owner, team (create: owner) |
| Tasks | `/studio/tasks/` | Owner, team |
| Quotation builder (rooms → items, live GST totals, PDF) | `/studio/quotations/` | Owner, team (accept/reject: owner) |
| Invoices & payments (outstanding, overdue, record payment, PDF) | `/studio/invoices/` | Owner records payments |
| Vendors | `/studio/vendors/` | Owner, team |
| Materials catalogue (rates used in quotations) | `/studio/catalogue/` | Owner, team |
| Studio settings (brand, colours, GST, schedule, rates, modules) | `/studio/settings/` | Owner |

### Money flow

1. **Quotation** — pick a project (or a lead), add rooms and items from the catalogue; totals with
   CGST + SGST (or IGST for other states) update live and autosave. Numbers: `QT/2026-27/001`.
2. **Send** — the quotation becomes read-only; share the PDF on WhatsApp. **Revise** creates v2.
3. **Accept** (owner) — creates the payment schedule from *Studio settings → GST & payments*
   (10% / 40% / 40% / 10% by default); amounts always add up to the grand total.
4. **Invoice** — raise each milestone from the project's *Billing* tab. Invoice numbers run per Indian
   financial year (`INV/2026-27/0001`, restarting on 1 April).
5. **Payment** — record UPI / bank transfer / cash / cheque; the invoice turns Partly paid → Paid and the
   dashboard's *Pending payments* and *Revenue this month* update instantly.

PDFs use the bundled Noto Sans font (`static/fonts`, SIL Open Font Licence) so the ₹ sign prints correctly.

**Convert to client + project** (owner, on a lead) creates the project, five default milestones and a
client-portal login (`c<mobile>` / `demo12345` in demo mode; a random password otherwise).

## Client portal

Sign in as `client` / `demo12345` (or **View as → Client**) and open `/portal/`. Mobile-first, with a bottom
tab bar on phones. Each client sees only their own project(s); every query is scoped to the signed-in client.

| Page | What the client can do |
|---|---|
| Overview | Progress, next milestone, designer contact, “action needed” cards |
| Designs | See every shared version, **approve**, **request changes**, or **comment on a specific image** |
| Timeline | Milestones with dates and status |
| Site updates | Weekly photos and notes from site |
| Documents | Quotation & invoice PDFs, agreement, drawings (permission-checked downloads) |
| Payments | Schedule, invoices, paid/due; *Pay online* is a locked full-version teaser |
| Requests & snags | Report an issue with a photo — it becomes a task for the designer |

**Live in the studio:** approvals, change requests, comments and requests appear on the owner's dashboard
(“From your clients”) and as a toast on any studio page within ~20 seconds. Approving a design marks the
*Design approval* milestone done; requesting changes creates a high-priority task for the designer.

## AI assistants (RAG)

| Assistant | Where | Answers from |
|---|---|---|
| **Design Assistant** | Floating “Ask AI” button on every website page (when the AI module is on) | Public documents only |
| **Studio Assistant** | `/studio/assistant/` | Public **and** internal documents (SOPs, vendor terms, policies) |

How it works: questions are matched against the knowledge base with BM25 (`rank-bm25`); the top 5
passages (~800 characters each) are the assistant's only sources. Answers are short, cite sources as
[1], [2] (shown under the answer), never invent prices or timelines, and end with a next step
(book a consultation / get an estimate). Ideas questions also show 2–3 matching portfolio projects.
If a visitor types their name and mobile number, a **lead with source “AI assistant”** is created with
the chat attached.

**Knowledge base** (`/studio/ai/`): 12 hand-written guides plus every FAQ, service and portfolio project
(synced automatically when they're saved). Upload PDF/TXT files (text extracted with `pypdf`), re-index,
and use **Test the assistant** to show the retrieved passages next to the answer. Chat logs: `/studio/ai/chats/`.
Command line: `python manage.py reindex_kb`.

**Offline vs Claude:** with `AI_MOCK=True` or no `ANTHROPIC_API_KEY`, answers are extractive (quoted from the
best passages) — free and offline. To use Claude, set in `.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
AI_MOCK=False
ANTHROPIC_MODEL=claude-opus-5-5     # default; any current Claude model works
ANTHROPIC_FALLBACKS=True            # server-side refusal fallback on supported models
```

Claude answers use effort `low` (short chat answers), a 30-second timeout, and fall back to the offline
answer on any API error or refusal, so the demo never breaks. Safety: retrieved text and visitor messages
are treated as data, not instructions; output is never executed and is rendered as sanitised text
(markdown → `bleach`); no tools; rate limits (15 messages / 10 min per chat, 40 / hour per IP); 500-character
messages.

## Switching roles in the demo

The demo ribbon has a **View as** menu: Visitor, Designer-owner, Team member, Client.
It signs you in as the demo user for that role — no passwords during a sales call. Disabled when `DEMO_MODE=False`.

## Automations (`/studio/automations/`)

Six automations work in the demo — booking confirmation, reminder 1 day before a consultation,
“quotation sent”, payment due reminder, new-lead alert to the owner, and follow-up for leads untouched for 3 days.
Messages are built from **editable templates** (owner can edit, switch off or restore each one) and shown as
WhatsApp-style previews. **Nothing is sent**: every message is logged with a **Send via WhatsApp** (`wa.me`) button,
and appears as a live toast in the studio. Event automations fire instantly; the daily checks run with
`python manage.py run_automations` (schedule it once a day with Task Scheduler / cron) or the
**Run daily checks now** button. Locked (full version): WhatsApp Business API auto-send, Instagram/Facebook lead ads,
Google Calendar sync, email campaigns, Google review requests.

## Sales story (demo mode only)

- **Guided tour** — **Tour** button in the demo ribbon (or `/?tour=1`). 12 steps from visitor → owner → client,
  switching roles automatically; arrow keys / Esc work; progress is remembered while you click around.
- **`/why`** — problems → solutions, the six modular packages (“Talk to us”, no prices), the **offer builder**
  (tick modules → clean summary, WhatsApp/print) and the **value calculator** (illustrative, based only on the
  prospect's own inputs and assumptions).
- Package names, descriptions and optional price text: **Admin → Website → Packages** (prices empty by default).
  Easy-payment lines: **Studio settings**.
- **Team & roles** (`/studio/team/`, owner): add team members, deactivate logins, see what each role can do.
  Advanced roles and payroll are locked teasers.
- **Full version** items in the studio sidebar, the case study (3D, AR), invoices (payment link) and portal
  open the “I want this feature” modal. Hide them all with *Show locked teasers* in Studio settings.

## Product landing page & enquiries (`/`)

In demo mode `/` is the DEVNIXPLUS sales page for interior designers: problems → solutions, the six modules with
screenshots, the client journey, packages (from **Admin → Website → Packages**), live-demo buttons (visitor / owner /
client), FAQ and an **enquiry form**. Enquiries land in **Admin → Core → Product enquiries** (`/admin/`, login
`admin`): status (New → Contacted → Demo scheduled → Proposal sent → Won/Lost), notes, one-click WhatsApp, filters,
and *Export selected to CSV*. The form has spam protection (hidden field + 5 per hour per connection).
`reset_demo` never deletes these enquiries; `setup_client` removes them from a client's copy.
Switched off by default: set `LANDING_PAGE=True` in `.env` and restart to make it the home page (`/`), with the studio home at `/demo/`. With it off, `/` is the studio home and `/demo/` and `/product/` redirect to `/`. It never shows when `DEMO_MODE=False`.
Landing images are in `static/img/landing/` — replace them with fresh screenshots any time.

## Website CMS (`/studio/website/`, owner)

Homepage and about text, portfolio projects (details, cover, gallery upload with automatic resizing, before/after
pairs, mood-board rooms and colour/material swatches), services, testimonials (with the “Sample” flag) and FAQs.
Changes are live immediately and re-indexed for the AI assistant.

## Reports (`/studio/reports/`)

Leads by source with conversion, revenue by month, outstanding payments with ageing, latest payments — for the last
3, 6 or 12 months. CSV export (opens in Excel with ₹ and Indian names intact; formula injection is neutralised).

## Booking settings

Weekly availability, slot length and blocked dates are edited in **Admin → Bookings**. Slots need 2 hours'
notice and can be booked up to 21 days ahead. The database refuses two active bookings in the same slot.
Estimator rates (₹/sq ft per finish level) are in **Admin → Studio settings**.
