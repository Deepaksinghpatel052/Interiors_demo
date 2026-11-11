"""Finance demo data: vendors, catalogue, quotations (draft/sent/accepted/revised), invoices and payments."""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.utils import timezone

from crm.models import Lead
from finance import services
from finance.models import CatalogueItem, Invoice, Quotation, Vendor
from studio.models import ClientProject

VENDORS = [
    ("Shree Ganesh Plywood", "plywood", "Mahesh Agrawal", "9826100101", "Indore", "30 days credit"),
    ("Mehta Laminates & Veneers", "laminate", "Rakesh Mehta", "9826100102", "Indore", "50% advance, balance on delivery"),
    ("Precision Hardware House", "hardware", "Sandeep Jain", "9826100103", "Indore", "Cash on delivery"),
    ("Lumina Lights", "lighting", "Farhan Sheikh", "9826100104", "Bhopal", "15 days credit"),
    ("Rang Décor Furnishings", "fabric", "Kavita Rathore", "9826100105", "Indore", "50% advance"),
    ("StoneCraft Marbles", "stone", "Ajay Patidar", "9826100106", "Indore", "Full payment before dispatch"),
    ("ColourHome Paints", "paint", "Vinod Sharma", "9826100107", "Indore", "Weekly billing"),
    ("AquaLuxe Bath Studio", "sanitary", "Neeraj Gupta", "9826100108", "Bhopal", "30% advance"),
    ("Vishwakarma Woodworks", "furniture", "Ramesh Vishwakarma", "9826100109", "Indore", "Running bills, weekly"),
    ("Sparkle Site Services", "services", "Anil Yadav", "9826100110", "Indore", "On completion"),
]

# name, category, vendor index, unit, rate, gst, hsn
ITEMS = [
    ("BWP plywood 18 mm (IS 710)", "plywood", 0, "sqft", 145, 18, "4412"),
    ("MR plywood 18 mm (IS 303)", "plywood", 0, "sqft", 96, 18, "4412"),
    ("HDHMR board 18 mm", "plywood", 0, "sqft", 112, 18, "4411"),
    ("Blockboard 19 mm", "plywood", 0, "sqft", 118, 18, "4412"),
    ("Matte laminate 1 mm", "laminate", 1, "sqft", 62, 18, "4823"),
    ("Acrylic high-gloss shutter finish", "laminate", 1, "sqft", 385, 18, "3920"),
    ("Natural teak veneer with PU polish", "laminate", 1, "sqft", 340, 18, "4408"),
    ("Fluted MDF panel, painted", "laminate", 1, "sqft", 290, 18, "4411"),
    ("Soft-close hinge (Hettich)", "hardware", 2, "nos", 420, 18, "8302"),
    ("Tandem drawer system (set)", "hardware", 2, "set", 3250, 18, "8302"),
    ("Sliding wardrobe system (2 shutters)", "hardware", 2, "set", 9800, 18, "8302"),
    ("Magic corner unit", "hardware", 2, "nos", 18500, 18, "8302"),
    ("Tall pantry pull-out", "hardware", 2, "nos", 22500, 18, "8302"),
    ("Aluminium profile handle", "hardware", 2, "rft", 340, 18, "7604"),
    ("COB downlight 12 W", "lighting", 3, "nos", 950, 18, "9405"),
    ("LED profile / cove light", "lighting", 3, "rft", 420, 18, "9405"),
    ("Decorative pendant light", "lighting", 3, "nos", 6800, 18, "9405"),
    ("New electrical point with wiring", "lighting", 3, "nos", 1150, 18, "8536"),
    ("Curtains with lining, stitched", "fabric", 4, "rft", 680, 12, "6303"),
    ("Roller blinds", "fabric", 4, "sqft", 165, 12, "6303"),
    ("Upholstered headboard panel", "fabric", 4, "sqft", 950, 18, "9403"),
    ("Quartz countertop 15 mm", "stone", 5, "sqft", 720, 18, "6810"),
    ("Italian marble flooring, laid", "stone", 5, "sqft", 640, 18, "6802"),
    ("Vitrified tiles 2×4, laid", "stone", 5, "sqft", 128, 18, "6907"),
    ("Kota stone, leather finish", "stone", 5, "sqft", 95, 5, "6802"),
    ("Royal emulsion painting (2 coats)", "paint", 6, "sqft", 32, 18, "3209"),
    ("Texture paint feature wall", "paint", 6, "sqft", 88, 18, "3209"),
    ("Designer wallpaper, fixed", "paint", 6, "sqft", 115, 18, "4814"),
    ("Vanity unit with basin", "sanitary", 7, "nos", 28500, 18, "9403"),
    ("Glass shower partition", "sanitary", 7, "sqft", 780, 18, "7007"),
    ("Modular kitchen base unit", "furniture", 8, "rft", 9600, 18, "9403"),
    ("Modular kitchen wall unit", "furniture", 8, "rft", 6400, 18, "9403"),
    ("Wardrobe, laminate finish", "furniture", 8, "sqft", 1380, 18, "9403"),
    ("TV unit with storage", "furniture", 8, "rft", 4900, 18, "9403"),
    ("Bed with hydraulic storage (queen)", "furniture", 8, "nos", 48000, 18, "9403"),
    ("Study table with overhead storage", "furniture", 8, "nos", 18500, 18, "9403"),
    ("Crockery unit with glass shutters", "furniture", 8, "rft", 7200, 18, "9403"),
    ("Pooja unit with jaali and backlight", "furniture", 8, "nos", 38000, 18, "9403"),
    ("Gypsum false ceiling", "furniture", 8, "sqft", 98, 18, "6809"),
    ("Linear workstation (per seat)", "furniture", 8, "nos", 14500, 18, "9403"),
    ("Glass partition with frosting", "furniture", 8, "sqft", 540, 18, "7007"),
    ("Acoustic wall panels", "furniture", 8, "sqft", 395, 18, "6808"),
    ("Carpet tiles, laid", "furniture", 8, "sqft", 98, 12, "5703"),
    ("Interior design fee", "services", None, "ls", 45000, 18, "998391"),
    ("Site supervision", "services", 9, "job", 28000, 18, "998391"),
    ("Deep cleaning before handover", "services", 9, "job", 6500, 18, "998533"),
    ("Civil work: demolition & masonry", "services", 9, "sqft", 68, 18, "995414"),
]

HOME_TEMPLATE = [
    ("Living & dining", [("TV unit with storage", 10), ("Crockery unit with glass shutters", 6), ("Fluted MDF panel, painted", 48),
                         ("Gypsum false ceiling", 260), ("COB downlight 12 W", 12), ("LED profile / cove light", 36),
                         ("Royal emulsion painting (2 coats)", 720), ("Curtains with lining, stitched", 18)]),
    ("Kitchen", [("Modular kitchen base unit", 14), ("Modular kitchen wall unit", 12), ("Quartz countertop 15 mm", 42),
                 ("Magic corner unit", 1), ("Tall pantry pull-out", 1), ("Tandem drawer system (set)", 6), ("Soft-close hinge (Hettich)", 18)]),
    ("Master bedroom", [("Wardrobe, laminate finish", 72), ("Sliding wardrobe system (2 shutters)", 1), ("Bed with hydraulic storage (queen)", 1),
                        ("Upholstered headboard panel", 40), ("Gypsum false ceiling", 180), ("LED profile / cove light", 28),
                        ("Royal emulsion painting (2 coats)", 520), ("Curtains with lining, stitched", 14)]),
    ("Kids' room", [("Wardrobe, laminate finish", 56), ("Study table with overhead storage", 1), ("Texture paint feature wall", 110),
                    ("Royal emulsion painting (2 coats)", 430), ("Roller blinds", 40)]),
    ("Pooja & foyer", [("Pooja unit with jaali and backlight", 1), ("Designer wallpaper, fixed", 60), ("Decorative pendant light", 1)]),
    ("Design & site management", [("Interior design fee", 1), ("Site supervision", 1), ("Deep cleaning before handover", 1)]),
]
OFFICE_TEMPLATE = [
    ("Open workspace", [("Linear workstation (per seat)", 36), ("Carpet tiles, laid", 1800), ("Gypsum false ceiling", 1800),
                        ("COB downlight 12 W", 60), ("New electrical point with wiring", 48)]),
    ("Cabins & meeting rooms", [("Glass partition with frosting", 640), ("Acoustic wall panels", 320), ("Natural teak veneer with PU polish", 180),
                                ("LED profile / cove light", 120)]),
    ("Reception & pantry", [("Fluted MDF panel, painted", 140), ("Quartz countertop 15 mm", 36), ("Modular kitchen base unit", 10),
                            ("Decorative pendant light", 3)]),
    ("Design & site management", [("Interior design fee", 1), ("Site supervision", 1), ("Deep cleaning before handover", 1)]),
]
FIXED_UNITS = {"ls", "job"}
COUNTED_UNITS = {"nos", "set", "sheet"}

# lead/project name -> (scenario, budget target ₹, days ago quotation date)
PROJECT_PLAN = {
    "Verma Residence, Vijay Nagar": ("approval", None, 56),
    "Dubey Villa, Arera Colony": ("execution", None, 112),
    "Studio North Office": ("ordering", None, 84),
    "Siddiqui 2BHK, MP Nagar": ("sent", None, 6),
    "Tomar Duplex, City Centre": ("handover", None, 150),
    "Bansal Home, Nipania": ("completed", None, 185),
}
# number of milestones paid / invoiced per scenario
SCENARIO = {
    "approval": {"paid": 1, "invoice_open": [1]},
    "execution": {"paid": 2, "partial": [2]},
    "ordering": {"paid": 2},
    "handover": {"paid": 3, "invoice_open": [3]},
    "completed": {"paid": 4},
}


def _fill(q, template, target):
    catalogue = {c.name: c for c in CatalogueItem.objects.all()}
    payload = {"title": q.title, "terms": q.terms, "client_address": q.client_address, "valid_until": str(q.valid_until),
               "rooms": [{"name": room, "items": [{
                   "catalogue_id": catalogue[name].pk, "description": catalogue[name].name, "unit": catalogue[name].unit,
                   "quantity": str(qty), "rate": str(catalogue[name].rate), "discount_percent": "0",
                   "gst_percent": str(catalogue[name].gst_percent), "hsn_code": catalogue[name].hsn_code}
                   for name, qty in items]} for room, items in template]}
    services.save_builder(q, payload)
    if target and q.grand_total:
        # Scale quantities so the quotation lands near the project's budget (fixed-price lines stay as they are).
        factor = Decimal(target) / q.grand_total
        for room in payload["rooms"]:
            for it in room["items"]:
                if it["unit"] in FIXED_UNITS:
                    continue
                step = Decimal(1) if it["unit"] in COUNTED_UNITS else Decimal("0.5")
                scaled = (Decimal(it["quantity"]) * factor / step).quantize(Decimal(1)) * step
                it["quantity"] = str(max(Decimal(1), scaled))
        # A small negotiated discount on furniture lines looks realistic
        for it in payload["rooms"][0]["items"][:2]:
            it["discount_percent"] = "5"
        services.save_builder(q, payload)
    return q


def _backdate(q, days_ago, sent_after=1):
    now = timezone.now()
    Quotation.objects.filter(pk=q.pk).update(
        date=(now - timedelta(days=days_ago)).date(), valid_until=(now - timedelta(days=days_ago - 30)).date(),
        sent_at=now - timedelta(days=days_ago - sent_after) if q.status != "draft" else None,
        decided_at=now - timedelta(days=days_ago - sent_after - 3) if q.status in ("accepted", "rejected") else None)


def seed_finance(stdout):
    if Vendor.objects.exists() or Quotation.objects.exists():
        return
    owner = User.objects.get(username="owner")
    vendors = [Vendor.objects.create(name=n, category=c, contact_person=p, phone=ph, city=city, payment_terms=t)
               for n, c, p, ph, city, t in VENDORS]
    for name, cat, vi, unit, rate, gst, hsn in ITEMS:
        CatalogueItem.objects.create(name=name, category=cat, vendor=vendors[vi] if vi is not None else None,
                                     unit=unit, rate=rate, gst_percent=gst, hsn_code=hsn)
    stdout.write(f"Vendors: {len(vendors)}, catalogue items: {len(ITEMS)}")

    today = timezone.localdate()
    pending_invoices = []  # (date, schedule item, paid?, partial?)
    for project in ClientProject.objects.select_related("lead"):
        plan = PROJECT_PLAN.get(project.name)
        if not plan:
            continue
        scenario, _, days_ago = plan
        q = services.create_quotation(project=project, user=owner,
                                      title="Office interiors — design & turnkey execution" if project.property_type == "office"
                                      else "Home interiors — design & turnkey execution")
        _fill(q, OFFICE_TEMPLATE if project.property_type == "office" else HOME_TEMPLATE, project.budget)
        services.send_quotation(q, owner)
        if scenario == "sent":
            _backdate(q, days_ago)
            continue
        items = services.accept_quotation(q, owner)
        _backdate(q, days_ago)
        start = today - timedelta(days=days_ago)
        span = max(10, (days_ago - 5))
        rules = SCENARIO[scenario]
        for i, item in enumerate(items):
            inv_date = start + timedelta(days=int(span * i / max(1, len(items) - 1)) if len(items) > 1 else 0)
            if i < rules["paid"]:
                pending_invoices.append((inv_date, item, "paid"))
            elif i in rules.get("partial", []):
                pending_invoices.append((today - timedelta(days=15), item, "partial"))
            elif i in rules.get("invoice_open", []):
                pending_invoices.append((today - timedelta(days=3), item, "open"))

    # Raise invoices in date order so numbers run chronologically (and roll over on 1 April)
    for inv_date, item, state in sorted(pending_invoices, key=lambda x: x[0]):
        inv = services.raise_invoice(item, owner, on_date=inv_date)
        if state == "paid":
            pay_date = min(today, inv_date + timedelta(days=3))
            mode = ["upi", "bank_transfer", "cheque", "upi"][item.order % 4]
            services.record_payment(inv, amount=inv.total, mode=mode, on_date=pay_date,
                                    reference=f"UTR{inv.pk:04d}{item.pk:05d}" if mode != "cheque" else f"CHQ {104500 + inv.pk}",
                                    user=owner)
        elif state == "partial":
            services.record_payment(inv, amount=(inv.total / 2).quantize(Decimal(1)), mode="bank_transfer",
                                    on_date=today - timedelta(days=10), reference=f"UTR{inv.pk:04d}P", user=owner)

    # Quotations for leads still deciding
    for name, scenario in [("Sana Khan", "sent"), ("Rajeev Nair", "revised"), ("Arvind Goyal", "draft")]:
        lead = Lead.objects.filter(name=name).first()
        if not lead:
            continue
        q = services.create_quotation(lead=lead, user=owner,
                                      title="Showroom interiors" if lead.property_type == "retail" else "Home interiors proposal")
        target = {"5_10": 750000, "10_20": 1350000}.get(lead.budget_band, 900000)
        _fill(q, HOME_TEMPLATE[:2] + HOME_TEMPLATE[-1:], target)
        if scenario == "draft":
            continue
        services.send_quotation(q, owner)
        _backdate(q, 14 if scenario == "sent" else 20)
        if scenario == "revised":
            services.reject_quotation(Quotation.objects.get(pk=q.pk), owner)
            v2 = services.revise_quotation(Quotation.objects.get(pk=q.pk), owner)
            v2.notes = "Revised as discussed: lighter kitchen finish and 5% discount on furniture."
            v2.save(update_fields=["notes"])
            for room in v2.rooms.all():
                room.items.update(discount_percent=5)
            v2.recalculate()
            services.send_quotation(v2, owner)
            _backdate(v2, 6)
    stdout.write(f"Quotations: {Quotation.objects.count()}, invoices: {Invoice.objects.count()}")
