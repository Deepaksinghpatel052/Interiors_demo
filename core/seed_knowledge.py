"""Knowledge base for the assistants: hand-written guides + automatic sync of FAQs, services and portfolio."""
from assistant import rag
from assistant.models import KnowledgeDocument
from assistant.sync import sync_all

P, I = "public", "internal"

DOCS = [
    ("About {name}", "process", P, """{name} is a design-led interior studio based in {city}, working since {year}. We design and build homes (1, 2 and 3 BHK apartments, villas and independent houses), modular kitchens, wardrobes, offices, clinics, cafés and showrooms.

One team handles design and execution, so the design you approve is the space you get. Every client gets a private online portal to see designs, approve them, track the timeline, download quotations and invoices, see payments and site photos, and raise requests.

Studio hours: {hours}. Address: {address}. Call {phone} or WhatsApp us any time."""),

    ("Our process & timelines", "process", P, """Our process has five steps: consultation, site visit, design and 3D, execution, and handover.

1. Free consultation (30 minutes) online, at our studio or at your site. We understand how you live, your budget and your timeline.
2. Site visit and measurements. We measure every wall, check electrical and plumbing points and photograph the space.
3. Design and 3D. Layouts, mood boards and 3D views are shared in your client portal. You approve them version by version or request changes.
4. Execution. Our supervised team builds the interiors, with weekly photo updates in your portal.
5. Handover. Deep cleaning, styling and a walkthrough, after which your warranty begins.

Typical timelines: design takes 2-3 weeks. Execution takes 6-8 weeks for a typical 2BHK and 8-12 weeks for a 3BHK, counted after the design and materials are approved. A modular kitchen alone takes 4-6 weeks; wardrobes 3-5 weeks. Villas and offices are planned individually. Your exact timeline is written in your proposal."""),

    ("Payment terms & schedule", "policy", P, """Payments are linked to project milestones, so you always pay for progress you can see:
- 10% booking advance when you confirm the project
- 40% on approval of the design
- 40% at mid-execution
- 10% on handover

Every payment gets a GST invoice, and you can see the schedule, invoices and receipts in your client portal. We accept UPI, bank transfer (NEFT, RTGS or IMPS), cheque and cash. Quotations are itemised with GST and are valid for 30 days. Civil, electrical and plumbing work is quoted separately unless it is listed in the quotation."""),

    ("Warranty policy", "policy", P, """Workmanship carries a 1-year warranty from the date of handover. Modular furniture (kitchens, wardrobes and storage units) carries a 5-year warranty against manufacturing defects. Branded hardware such as hinges, channels and lift-ups carries the manufacturer's own warranty, which we help you claim.

The warranty does not cover damage from water leakage in walls, misuse, or changes made by other contractors. To raise a warranty request, use 'Requests & snags' in your client portal or WhatsApp us with a photo; we usually visit within 3 working days."""),

    ("Materials guide: plywood, laminates and finishes", "material", P, """Plywood: we use BWP (boiling water proof, IS 710) plywood for kitchens, bathrooms and other wet areas, and MR (moisture resistant, IS 303) plywood for wardrobes and dry areas. HDHMR board is an option for shutters on a tighter budget.

Finishes: matte laminates (1 mm) are durable, easy to clean and the most popular choice. Acrylic gives a high-gloss modern look. Natural veneer with PU polish gives a warm, premium wood finish. Fluted and painted MDF panels are used for feature walls.

Countertops: quartz is non-porous and stain resistant, ideal for Indian cooking. Granite is a durable budget alternative.

Hardware: we use soft-close hinges and drawer systems from brands such as Hettich and Hafele. Every material, brand and thickness is listed in your quotation, and you can see samples at our studio."""),

    ("Consultation & design fees", "policy", P, """The first consultation (30 minutes) is free and has no obligation. You can have it online, at our studio, or at your site.

For full projects, the design fee is included in the turnkey quotation and shown as a separate line. For design-only work (layouts, colour scheme, material selection and a shopping list you execute yourself) we quote a fixed design fee after understanding the scope. Site visits within the city are free during a project; projects outside the city include travel and stay, quoted separately."""),

    ("Care & maintenance of your interiors", "material", P, """Laminates and acrylic: wipe with a soft damp cloth and mild soap; avoid abrasive scrubbers. Veneer and PU finishes: dust regularly and keep away from direct water. Quartz countertops: clean with soap and water; avoid placing hot pans directly on the surface. Hinges and channels: avoid hanging heavy weights on shutters. If a shutter drops or a channel feels stiff, raise a request in your client portal — small adjustments are free in the warranty period."""),

    ("GST & invoicing", "policy", P, """All our quotations and invoices include GST. Interior design and execution services are invoiced with CGST and SGST for clients within our state, and IGST for clients in other states. Each milestone payment gets its own tax invoice with our GSTIN. Businesses can share their GSTIN to claim input tax credit. Invoices and quotations can be downloaded any time from the client portal."""),

    # ---------------------------------------------------------------- internal
    ("Site-visit SOP (internal)", "process", I, """Before the visit: confirm the time on WhatsApp the day before, carry the laser measure, tape, moisture meter and the site-visit checklist, and review the lead's notes and style-quiz result.

At site: photograph every wall from the doorway, measure each room including ceiling height, mark all electrical and plumbing points, note beams and columns, check for dampness with the moisture meter, and confirm possession date and society work rules (timings, lift use, debris).

After the visit: upload photos and measurements to the project within 24 hours, update the lead stage to 'Site visit', and set a follow-up date. Share the layout options within 5 working days."""),

    ("Vendor terms & ordering (internal)", "policy", I, """Ordering is done only after the client approves the design and the 40% design-approval payment is received. Raise orders from the materials catalogue rates; any vendor rate above the catalogue rate needs owner approval.

Shree Ganesh Plywood: 30 days credit. Mehta Laminates & Veneers: 50% advance, balance on delivery. Precision Hardware House: cash on delivery. StoneCraft Marbles: full payment before dispatch; quartz lead time 10-12 days. Lumina Lights: 15 days credit. Check every delivery against the order and photograph labels (brand, thickness, IS mark) before accepting."""),

    ("Snag & handover checklist (internal)", "process", I, """Seven days before handover, do a full snag walk with the supervisor: check every shutter alignment and soft-close, drawer movement, edge banding, laminate scratches, paint touch-ups, electrical points and lights, and silicone around wet areas. Log each snag as a task with a photo and fix within 5 days.

Handover day: deep cleaning done, all keys and warranty cards in a folder, a care guide shared, and a walkthrough with the client. Raise the final 10% invoice after the client signs off. Ask for a Google review a week after handover."""),

    ("Discounts & escalation policy (internal)", "policy", I, """Designers can offer up to 5% discount on furniture lines without approval. Anything above 5%, or any discount on services and design fee, needs the owner's approval before the quotation is sent. Never promise dates or prices on WhatsApp that are not in the accepted quotation.

Escalations: any client complaint, delay of more than 7 days, or payment overdue by more than 10 days goes to the owner the same day. Safety issues at site stop work immediately and are reported to the owner."""),
]


def seed_knowledge(stdout, settings_obj):
    if KnowledgeDocument.objects.filter(source_key__isnull=True).exists():
        return
    fmt = {"name": settings_obj.name, "city": settings_obj.city, "year": settings_obj.founded_year,
           "hours": settings_obj.working_hours, "address": settings_obj.address, "phone": settings_obj.phone}
    for title, doc_type, audience, content in DOCS:
        KnowledgeDocument.objects.create(title=title.format(**fmt), doc_type=doc_type, audience=audience,
                                         content=content.format(**fmt))
    sync_all()
    rag.bump_version()
    stdout.write(f"Knowledge base: {KnowledgeDocument.objects.count()} documents "
                 f"({len(DOCS)} guides + synced FAQs, services and portfolio)")
    seed_chats()


def seed_chats():
    """Two sample website conversations (answered offline), one of which became a lead."""
    from datetime import timedelta

    from django.utils import timezone

    from assistant import llm
    from assistant.models import ChatMessage, ChatSession
    from crm.models import Lead

    if ChatSession.objects.exists():
        return
    convos = [
        (3, None, ["How long does a 2BHK interior take?", "What warranty do you give on the kitchen?"]),
        (1, "Fatima Ansari", ["Which plywood do you use in the kitchen?", "How long does a modular kitchen take?",
                              "My name is Fatima Ansari, please call me on 98266 33221"]),
    ]
    for days_ago, lead_name, questions in convos:
        session = ChatSession.objects.create(channel=ChatSession.Channel.PUBLIC)
        when = timezone.now() - timedelta(days=days_ago)
        history = []
        for i, q in enumerate(questions):
            a = llm.answer(q, "public", history) if "call me" not in q else llm.Answer(
                text="Thank you, Fatima! Our designer will call you on 9826633221 within one working day.", mode="lead")
            for role, text, sources, mode in [("user", q, [], ""), ("assistant", a.text, a.sources, a.mode)]:
                m = ChatMessage.objects.create(session=session, role=role, text=text, sources=sources, mode=mode)
                ChatMessage.objects.filter(pk=m.pk).update(created_at=when + timedelta(minutes=i * 2))
            history += [{"role": "user", "text": q}, {"role": "assistant", "text": a.text}]
        if lead_name:
            session.lead = Lead.objects.filter(name=lead_name).first()
            session.save(update_fields=["lead"])
        ChatSession.objects.filter(pk=session.pk).update(created_at=when, last_at=when + timedelta(minutes=6))
