# 10-minute demo script

For a screen-share or an in-person meeting with an interior designer (owner of a small studio).
Goal: they should *feel* their own studio running on it, then choose a package.

## Before the call (5 minutes)

1. `python manage.py reset_demo --offline` — clean data (or rely on the nightly reset).
2. Rebrand for the prospect (their Instagram photos + logo, saved to a folder):
   `python manage.py brand_demo --name "Their Studio" --city "Their City" --phone "98XXXXXXXX" --logo logo.png --images photos\`
3. Open two browser windows: **laptop** (main) and the **phone view** (DevTools device mode or your own phone).
4. Have WhatsApp Web open — the “Talk to DEVNIXPLUS” and “I want this feature” buttons open it.

Tip: the **Tour** button in the black demo ribbon walks the same story with one sentence of benefit per step.
Use it if you are nervous; skip it if the conversation flows.

## The story (≈ 1 minute per step)

| # | Show | Say (benefit, in their words) |
|---|---|---|
| 1 | **Home page** on the phone. Scroll: hero, recent projects, “Next free consultation”, WhatsApp button. | “This is *your* website with *your* projects. Most clients find you on Instagram and then check if you are serious — this is what they see.” |
| 2 | **Portfolio** → open a project: gallery, **before/after slider**, mood board. | “Clients understand your work faster than from 50 Instagram posts. It looks premium, so they expect premium prices.” |
| 3 | **Style quiz** (30 seconds) → result with matching projects. | “Even people who can’t explain what they want get a style name — and you get their number.” |
| 4 | **Cost estimator**: 3 BHK, premium. | “Stops the ‘how much for a 2 BHK?’ calls. It gives a range, not a quote, and the lead lands in your ERP.” |
| 5 | **Ask AI** → “What warranty do you give?” / “Do you do site visits?” Point at the [1] citation. | **RAG in simple words:** “It doesn’t make things up. It first *finds* the answer in your own documents — FAQs, services, warranty — and then writes it nicely, showing where it came from. If it doesn’t know, it offers WhatsApp.” |
| 6 | **Book a consultation**: pick a slot, confirm. | “No back-and-forth. Only free slots are shown; no double booking.” |
| 7 | Switch to **Owner** (ribbon → View as). **Leads board**: the new booking/lead is on top. Drag a card. Then **Bookings calendar**. | **Wow moment #1.** “Every enquiry — website, Instagram, walk-in — in one place. Nothing lost in WhatsApp.” |
| 8 | **Automations**: the booking confirmation is already written, “Send via WhatsApp”. | “Confirmations, reminders and payment nudges are written for you. One tap.” Mention locked: *WhatsApp Business API auto-send*. |
| 9 | **Quotations** → open one → **PDF**. Show GST split, payment schedule, bank details. | **Wow moment #3.** “A branded GST quotation in minutes, not a weekend in Excel.” |
| 10 | Switch to **Client** → **Designs**: approve a design / request changes with a comment. Switch back to Owner: the live toast appears. | **Wow moment #2.** “Approvals are recorded. No ‘I never said yes to this colour’.” Mention locked: *3D walkthrough, AR view*. |
| 11 | **Invoices** → record a payment (UPI). Then **Dashboard**: revenue and pending payments update. **Reports** → CSV. | **Wow moment #5.** “You always know who owes what.” Mention locked: *online payments (Razorpay), Tally export*. |
| 12 | **/why** page: problems → modules → packages. Tick modules in the **offer builder**. Fill the **value calculator** with *their* numbers. | “Start with what hurts most. Everything connects later.” Make clear the calculator is an example from their inputs, not a promise. |

## Which locked features to mention (pick 2–3, don’t list all)

- Studio with many site visits → **Mobile app for supervisors**, **attendance & payroll**.
- Studio that buys a lot of material → **Inventory & procurement**, **Tally export**.
- Studio running Instagram ads → **Lead ads sync**, **WhatsApp Business API**, **Google review requests**.
- Premium/luxury studio → **3D/360° walkthrough**, **AR view in your room**.
- Owner who wants answers fast → **AI “Ask your business data”**.

Clicking a locked item opens the modal; **“I want this feature”** records interest and opens WhatsApp to you —
a natural moment to note their priorities.

## Closing (1 minute)

- Ask: “Which two problems cost you the most time today?” → map to modules on `/why`.
- Offer the easy-payment option shown on the offer (editable in Studio settings).
- Next step: collect their logo, 15–30 project photos, services, FAQs, rates and GST details (see `NEW_CLIENT_SETUP.md`).

## Don’t

- Don’t promise numbers. Sample testimonials are labelled **Sample**; say so if asked.
- Don’t show the Django admin — everything is in the Studio.
- Don’t demo on a slow connection without `--offline` reset done beforehand.
