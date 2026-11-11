# Build plan — Interior Studio Demo (Django)

## Folder structure

```
interior_designer_demo/
├── venv/                     # project virtual environment (not committed)
├── config/                   # settings, root urls, wsgi/asgi
├── core/                     # StudioSettings (white-label + feature flags), demo ribbon,
│   │                         # role switcher, locked features, templatetags (₹, dates, WhatsApp)
│   └── management/commands/  # seed_demo, reset_demo, brand_demo, setup_client, reindex_kb
├── website/                  # public site + CMS content: portfolio, services, testimonials, FAQ,
│                             # mood boards, style quiz, cost estimator
├── crm/                      # Lead, LeadActivity (CRM pipeline)
├── bookings/                 # Availability, BlockedDate, Booking (slot engine, .ics)          [Phase 2]
├── studio/                   # ERP: dashboard, client projects, milestones, tasks, proposals
├── finance/                  # Vendors, catalogue, quotations, invoices, payments, PDFs
├── portal/                   # client portal views
├── assistant/                # KnowledgeDocument, Chunk, ChatLog, BM25 + Anthropic
├── automations/              # templates + automation log (simulated sends)                     [Phase 7]
├── templates/                # base.html, partials/, one folder per app
├── static/                   # css/studio.css (design system), js/site.js
├── media/                    # uploads + generated demo images (not committed)
└── docs/                     # PLAN, README-linked docs, DEMO_SCRIPT, MODULES, ROADMAP, NEW_CLIENT_SETUP
```

## Key models

| App | Models |
|---|---|
| core | `StudioSettings` (singleton: brand, contact, GST, rates, payment schedule, module flags), `FeatureInterest` |
| website | `PortfolioProject`, `ProjectImage`, `BeforeAfter`, `ProjectRoom`, `ProjectSwatch`, `TimelineStep`, `Service`, `Testimonial`, `FAQ`, `PhotoCredit` |
| crm | `Lead`, `LeadActivity` |
| bookings | `WeeklyAvailability`, `BlockedDate`, `Booking` |
| studio | `ClientProject`, `Milestone`, `Task`, `DesignProposal`, `ProposalImage`, `ProposalComment`, `SiteUpdate`, `ClientRequest`, `ProjectDocument` |
| finance | `Vendor`, `CatalogueItem`, `Quotation`, `QuotationRoom`, `QuotationItem`, `PaymentScheduleItem`, `Invoice`, `Payment` |
| assistant | `KnowledgeDocument`, `KnowledgeChunk`, `ChatSession`, `ChatMessage` |
| automations | `MessageTemplate`, `AutomationLog` |
| website (later) | `Package` (offer builder, empty prices by default) |

## URL map

| Area | URLs |
|---|---|
| Public | `/` `/portfolio/` `/portfolio/<slug>/` `/services/` `/about/` `/contact/` `/faq/` `/privacy/` `/photo-credits/` `/book/` `/estimate/` `/style-quiz/` `/moodboard/<slug>/` `/why/` |
| Demo | `/demo/role/<visitor|client|owner>/` `/demo/interest/<feature>/` |
| Portal | `/portal/` `/portal/designs/` `/portal/timeline/` `/portal/documents/` `/portal/payments/` `/portal/updates/` `/portal/requests/` |
| ERP | `/studio/` (dashboard) `/studio/leads/` `/studio/bookings/` `/studio/projects/` `/studio/quotations/` `/studio/invoices/` `/studio/vendors/` `/studio/catalogue/` `/studio/cms/` `/studio/reports/` `/studio/team/` `/studio/ai/` `/studio/automations/` |
| API (JSON, CSRF) | `/api/slots/` `/api/chat/` `/studio/leads/move/` `/studio/bookings/events/` |

## Phases

1. Project setup, venv, settings, StudioSettings, design system, public site (home, portfolio, case study, services, about, contact, FAQ, privacy) — **done**
2. Showcase tools (mood board, before/after, style quiz), cost estimator, consultation booking with slots — **done**
3. ERP core: dashboard, leads Kanban, bookings calendar, projects and tasks — **done**
4. Quotation builder, invoices and payments, vendors and catalogue, PDFs — **done**
5. Client portal with design approvals, timeline, documents, payments, requests — **done**
6. RAG knowledge base and both assistants (mock + Anthropic) — **done**
7. Automations preview, locked features and modals, guided tour, role switcher, `/why` page and value calculator — **done**
8. seed/reset/brand_demo/setup_client commands, module flags, tests, docs (+ ERP reports and Website CMS) — **done**
9. Quality pass: every page crawled as each role (normal and empty data), checked at 390px phone and 1366px laptop; fixed studio header overflow on phones, small touch targets, unlabelled form fields, enquiry form landing position — **done**
9. Quality pass (390 px phone + laptop)
