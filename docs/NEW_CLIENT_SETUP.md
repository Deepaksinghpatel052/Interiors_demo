# New client setup (launch in 1–2 days)

## Day 0 — collect from the client (send this list on WhatsApp)

**Brand**
- [ ] Studio name and legal name, logo (PNG with transparent background if possible), brand colour if they have one
- [ ] Tagline (one line) and a short “about us” (4–6 lines), year founded

**Contact**
- [ ] Phone, WhatsApp number, e-mail, full address (for the map), Instagram handle, working hours

**Work**
- [ ] 4–10 projects: title, area/city, room type, style, approx. budget band, sq ft, duration, 3–8 photos each,
      before/after pairs if any, client quote (only with permission)
- [ ] Services they offer (and what's included), typical timelines
- [ ] 8–15 FAQs (warranty, payment terms, timelines, site visits, materials) — these also train the AI assistant
- [ ] Real testimonials with permission (otherwise none — never publish samples)

**Money**
- [ ] GSTIN, state, default GST %, bank details / UPI ID, quotation terms
- [ ] Payment schedule (e.g. 10 / 40 / 40 / 10) and estimator rates per sq ft (essential / premium / luxury)
- [ ] Vendors and common materials with rates (optional — can start from the demo catalogue)

**People**
- [ ] Owner's name and preferred username; team members' names
- [ ] Consultation hours, days off, slot length

**Package**
- [ ] Modules bought: Website / CMS / Portal / ERP / Automation / AI · show locked teasers? (yes/no)

## Day 1 — configure

1. Fresh copy of the code on the server (see *Deploy* below), `.env` with a new `SECRET_KEY`, `DEBUG=False`,
   `ALLOWED_HOSTS=their-domain.in`, `DEVNIX_*` values, `ANTHROPIC_API_KEY` if AI is included.
2. `python manage.py migrate` then `python manage.py seed_demo --offline` (gives the structure: groups, templates).
3. Optional quick start with their photos: `python manage.py brand_demo --name … --city … --phone … --logo … --images …`
4. Hand over: `python manage.py setup_client --owner-username <name> --owner-name "<Full Name>" [--keep-content] [--keep-catalogue]`
   - Save the generated password and share it privately.
   - Restart the app (DEMO_MODE is now `False`: no ribbon, tour, `/why`, role switcher or nightly reset).
5. Sign in as the owner → **Studio settings**: brand, contact, GST/bank, rates, payment schedule, **Modules**.
6. **Website content**: homepage text, projects (replace/complete), services, FAQs, testimonials.
7. **Availability**: weekly hours and holidays.
8. **AI knowledge base** (if AI): review synced FAQs/services, add warranty, payment terms, process, materials guide
   (PDF upload works); use **Test the assistant** with 5 real questions.
9. **Automations** (if bought): adjust the message wording; schedule `run_automations` daily.
10. **Team & roles**: create team members.

## Day 2 — check and launch

- [ ] Phone check (390 px) and laptop: home, portfolio, a case study, booking, contact form, WhatsApp buttons
- [ ] Book a test consultation → appears in leads + calendar → delete it
- [ ] Create a test quotation → PDF: GSTIN, address, bank, terms correct → delete it
- [ ] Portal: convert a test lead, sign in as the client, approve a design → delete test data
- [ ] Privacy page reviewed; photo credits only for stock photos still used
- [ ] Backups scheduled (copy `db.sqlite3` + `media/` nightly)
- [ ] 30-minute training call with the owner (record it)

## Deploy (small VPS or PaaS)

```bash
python -m venv venv && venv/bin/pip install -r requirements.txt
cp .env.example .env            # edit: SECRET_KEY, DEBUG=False, ALLOWED_HOSTS, DEMO_MODE=False
venv/bin/python manage.py migrate
venv/bin/python manage.py collectstatic --noinput
venv/bin/pip install gunicorn   # serve with gunicorn behind nginx (or waitress on Windows)
```

- nginx: serve `/static/` from `staticfiles/` and `/media/` from `media/`; `client_max_body_size 10m;`; HTTPS via Let's Encrypt.
- Cron: `run_automations` daily at 08:00 IST (if Automation module); backups nightly.
- Never run `reset_demo` on a client server (it refuses when `DEMO_MODE=False`).
