"""Demo content for Aangan Interiors. All names, places and quotes are fictional samples."""

SERVICES = [
    ("Residential interiors", "residential-interiors", "house-heart",
     "Complete homes — 1, 2 and 3 BHK apartments, villas and independent houses.",
     "We design the whole home as one story: layouts that work for your family, storage that disappears, "
     "lighting that changes with the day, and finishes that age well in Indian weather.",
     "Space planning and furniture layout\nMood boards and 3D views\nFalse ceiling and lighting design\nFurniture, soft furnishings and décor\nSite supervision till handover",
     "8–14 weeks"),
    ("Modular kitchens", "modular-kitchens", "cup-hot",
     "Kitchens planned around Indian cooking — tadka, tawa and tiffin included.",
     "Ergonomic L, U, parallel and island kitchens with the right chimney, tall units, pull-outs and "
     "easy-clean surfaces. Built from BWP plywood with branded hardware.",
     "Work-triangle planning\nBWP plywood carcass, choice of finishes\nHettich / Hafele hardware\nChimney, hob and sink integration\nUnder-cabinet lighting",
     "4–6 weeks"),
    ("Wardrobes & storage", "wardrobes-storage", "door-closed",
     "Sliding, hinged and walk-in wardrobes with storage planned for every saree and suitcase.",
     "Every wardrobe is planned around what you actually own — long hangers, drawers, lofts, lockers and "
     "pull-out trays — with soft-close fittings throughout.",
     "Internal layout planning\nSliding or hinged shutters\nLoft and locker units\nProfile and sensor lighting",
     "3–5 weeks"),
    ("Office & commercial", "office-commercial", "briefcase",
     "Workspaces, clinics, cafés and showrooms that reflect your brand and work hard every day.",
     "We plan for people, flow and brand: workstations, cabins, meeting rooms, reception and display — "
     "executed with minimal disruption to your business.",
     "Space planning for teams\nBranding and signage integration\nAcoustic and lighting design\nAfter-hours execution on request",
     "6–12 weeks"),
    ("Renovation", "renovation", "arrow-repeat",
     "Give an older home a new life — without rebuilding it.",
     "From bathroom and kitchen upgrades to complete makeovers, we work with your existing structure, "
     "fix what is hidden, and update what you see.",
     "Condition survey and plan\nCivil, plumbing and electrical upgrades\nFlooring and wall finishes\nPhased work if you stay in the home",
     "4–10 weeks"),
    ("Turnkey execution", "turnkey-execution", "key",
     "One contract, one team, one handover date — design to move-in.",
     "We handle design, procurement, contractors, quality checks and deep cleaning, so you only need to "
     "approve designs and walk into a finished home.",
     "Single point of contact\nMilestone-based payments\nWeekly photo updates in your portal\nWarranty on workmanship",
     "10–16 weeks"),
    ("Design consultation", "design-consultation", "chat-square-heart",
     "Expert advice for a room, a layout or a colour decision — no full project needed.",
     "Ideal if you have a contractor and only need a professional eye: layouts, colour schemes, material "
     "selection and a shopping list you can execute yourself.",
     "60-minute consultation\nLayout sketch and colour palette\nMaterial and product recommendations",
     "1–2 weeks"),
]

TESTIMONIALS = [
    ("Priya & Rohit Agrawal", "Indore", "3 BHK, Vijay Nagar",
     "We could see every design and every payment in one place. No running behind anyone for updates — the weekly photos were enough."),
    ("Dr. Sameer Khan", "Bhopal", "Dental clinic",
     "The clinic was finished on the date they promised. Patients notice the calm space the moment they walk in."),
    ("Meenakshi Iyer", "Indore", "Modular kitchen",
     "They asked how I cook before they drew a single line. My kitchen finally has a place for everything."),
]

FAQS = [
    ("Process", "How does the design process work?",
     "We start with a free consultation, then a site visit for measurements. You receive layouts, mood boards and 3D views in your client portal, approve them version by version, and then we execute with weekly photo updates until handover."),
    ("Process", "How long does a 2BHK or 3BHK interior take?",
     "Design usually takes 2–3 weeks. Execution takes 6–8 weeks for a typical 2BHK and 8–12 weeks for a 3BHK after design and materials are approved. Your exact timeline is shared in your proposal."),
    ("Process", "Do you visit the site before quoting?",
     "Yes. A site visit with measurements is part of every proposal so the quotation reflects your actual space."),
    ("Cost & payments", "How much does interior design cost?",
     "It depends on area, scope and the finish level you choose. You can use our cost estimator for an indicative range; the exact quotation comes after the site visit and is itemised with GST."),
    ("Cost & payments", "What is your payment schedule?",
     "Payments are linked to milestones: 10% on booking, 40% on design approval, 40% at mid-execution and 10% at handover. You can track every payment in your client portal."),
    ("Cost & payments", "Which payment modes do you accept?",
     "UPI, bank transfer (NEFT/RTGS/IMPS), cheque and cash. Every payment gets a receipt and a GST invoice."),
    ("Materials & warranty", "Which materials do you use?",
     "We use BWP/BWR plywood for kitchens and bathrooms, MR plywood for dry areas, branded laminates and veneers, and branded hardware such as Hettich and Hafele. Every material is listed in your quotation."),
    ("Materials & warranty", "Do you offer a warranty?",
     "Yes. Workmanship carries a 1-year warranty and modular furniture a 5-year warranty against manufacturing defects. Branded hardware carries the manufacturer's warranty."),
    ("Working with us", "Can I see my designs online?",
     "Yes. Every client gets a private portal to see design versions, approve or request changes, view documents and quotations, track payments and see site photos."),
    ("Working with us", "Do you work outside the city?",
     "We take projects across the state. For projects outside the city, travel and stay for site visits are quoted separately."),
]

# title, room, style, budget, property, area, weeks, location, featured
PROJECTS = [
    ("The Courtyard Home", "full_home", "traditional", "20_40", "villa", 2800, 16, "Bicholi Mardana, Indore", True,
     "A family villa where a carved jharokha wall and a sunlit courtyard tie three generations together.",
     "A joint family wanted space for festivals, privacy for each generation and a home that felt rooted without feeling old."),
    ("Teal & Teak 2BHK", "living", "modern", "10_20", "2bhk", 1050, 10, "Vijay Nagar, Indore", True,
     "A compact 2BHK living room that feels twice its size, with teal upholstery and warm teak tones.",
     "A young couple working from home needed a living room that also hosts friends on weekends."),
    ("Ivory Calm Bedroom", "bedroom", "minimal", "5_10", "3bhk", 220, 5, "Arera Colony, Bhopal", False,
     "A quiet master bedroom in soft ivory with hidden storage and warm, low lighting.",
     "The brief was simple: a bedroom that switches off the day — no clutter, no glare."),
    ("Emerald Island Kitchen", "kitchen", "luxury", "10_20", "villa", 240, 6, "Shyamla Hills, Bhopal", True,
     "A dark, dramatic island kitchen with emerald shutters and brushed brass details.",
     "Keen home cooks who entertain often wanted a show kitchen that still handles everyday Indian cooking."),
    ("Studio North Office", "office", "contemporary", "20_40", "office", 3200, 12, "Scheme 54, Indore", True,
     "A 45-seat tech office with focus zones, a library wall and lots of daylight.",
     "A growing software team needed collaboration and quiet in the same floor plate."),
    ("Saffron Saree Boutique", "retail", "traditional", "10_20", "retail", 900, 7, "Rajwada, Indore", False,
     "A heritage-inspired saree boutique with warm display lighting and a central drape table.",
     "The owner wanted customers to feel the richness of the fabrics the moment they enter."),
    ("Monochrome 3BHK", "full_home", "minimal", "10_20", "3bhk", 1550, 12, "Nipania, Indore", False,
     "A clean, gallery-like 3BHK in whites and greys, softened with oak and linen.",
     "A family that loves to travel wanted a home that is easy to maintain and calm to come back to."),
    ("Heritage Haveli Bedroom", "bedroom", "traditional", "5_10", "4bhk", 260, 6, "Lashkar, Gwalior", False,
     "A guest suite with a hand-painted headboard, sheesham furniture and block-printed linen.",
     "A bedroom for visiting parents that feels familiar, festive and comfortable."),
    ("Sage Parallel Kitchen", "kitchen", "contemporary", "under_5", "2bhk", 110, 4, "Kolar Road, Bhopal", False,
     "A bright parallel kitchen in sage and white with smart corner storage.",
     "A first-home buyer wanted a practical, beautiful kitchen within a tight budget."),
    ("The Gold Room Lounge", "living", "luxury", "above_40", "villa", 650, 14, "Ring Road, Indore", True,
     "A double-height villa lounge in deep charcoal with gold accents and Italian marble.",
     "A family that hosts large gatherings wanted a living room with real presence."),
    ("Skyline Co-working Hub", "office", "modern", "above_40", "office", 6800, 16, "AB Road, Indore", False,
     "A 120-seat co-working floor with hot desks, phone booths, a café counter and city views.",
     "A co-working brand needed a floor that feels premium for start-ups but survives heavy daily use."),
    ("Founders’ Cabin, Arera Hills", "office", "luxury", "20_40", "office", 1200, 8, "Arera Hills, Bhopal", False,
     "A private director’s cabin and boardroom in walnut, leather and soft linear lighting.",
     "Two founders wanted a calm, impressive space to meet investors and large clients."),
    ("Noor Jewellers Showroom", "retail", "luxury", "20_40", "retail", 1400, 10, "Sarafa Bazaar, Indore", True,
     "A jewellery showroom with backlit display cases, a private bridal lounge and secure vault access.",
     "A third-generation jeweller wanted a modern showroom that still feels trustworthy and warm."),
    ("Brew & Bloom Café", "retail", "contemporary", "10_20", "retail", 1100, 8, "Palasia, Indore", False,
     "A 40-cover café with a brick-and-oak counter, hanging greens and Instagram-ready corners.",
     "First-time café owners needed a space that photographs well and turns tables fast."),
    ("Urban Nest 1BHK", "full_home", "minimal", "under_5", "1bhk", 520, 6, "Rau, Indore", False,
     "A compact 1BHK for a young professional — every wall works as storage, nothing feels crowded.",
     "A first-job home on a strict budget that still had to feel calm and grown-up."),
    ("Blue Hour Living Room", "living", "modern", "5_10", "2bhk", 280, 5, "Kolar Road, Bhopal", False,
     "A modern living room built around a sapphire sofa, a slatted TV wall and warm cove lighting.",
     "A couple who love colour wanted one bold statement without the room feeling loud."),
    ("Royal Suite Bedroom", "bedroom", "luxury", "above_40", "villa", 420, 9, "Ring Road, Indore", True,
     "A hotel-style master suite with an upholstered wall, dressing lounge and walk-in wardrobe.",
     "The owners wanted their bedroom to feel like their favourite five-star hotel suite."),
    ("Pearl White Island Kitchen", "kitchen", "modern", "5_10", "3bhk", 140, 5, "Nipania, Indore", False,
     "A bright white island kitchen with a quartz breakfast counter, slim handles and a tall pantry wall.",
     "A busy family wanted a kitchen that is quick to clean and has a place for everything."),
    ("Riverside Family Home", "full_home", "contemporary", "20_40", "4bhk", 2400, 14, "City Centre, Gwalior", False,
     "A four-bedroom family home in oak, sage and brass — open living, a formal dining and a home office.",
     "Three generations under one roof needed shared spaces for festivals and private corners for each."),
]

ROOMS_BY_TYPE = {
    "full_home": [("Living & dining", "An open plan with a 6-seater dining, a TV wall with concealed storage and layered lighting."),
                  ("Master bedroom", "A calm bedroom with a walk-in wardrobe and a reading corner by the window."),
                  ("Kitchen", "An L-shaped modular kitchen with a breakfast counter and tall pantry units."),
                  ("Pooja room", "A backlit jaali pooja unit with brass bells and storage for festival items.")],
    "living": [("Seating", "A modular sofa with a reversible chaise so the room adapts for guests."),
               ("TV & storage wall", "Fluted panels hide wiring, a set-top box and board games."),
               ("Lighting", "Cove lights for evenings, a floor lamp for reading and spots on the art.")],
    "bedroom": [("Bed & headboard", "An upholstered headboard wall with integrated side lights."),
                ("Wardrobe", "Floor-to-ceiling sliding wardrobe with a loft, locker and saree drawers."),
                ("Study nook", "A floating desk by the window for work and paperwork.")],
    "kitchen": [("Layout", "A planned work triangle between hob, sink and refrigerator."),
                ("Storage", "Tall pantry, magic corner, tandem drawers and a bottle pull-out."),
                ("Surfaces", "Quartz counter, anti-fingerprint shutters and an easy-clean backsplash.")],
    "office": [("Workstations", "Benching for 36 with cable management and personal lockers."),
               ("Meeting rooms", "Two glass meeting rooms with acoustic panels."),
               ("Café & library", "A pantry café and a library wall for quiet work.")],
    "retail": [("Display walls", "Back-lit shelving that shows colour and texture without glare."),
               ("Drape table", "A central table to unfold and try sarees in good light."),
               ("Trial room", "A spacious trial room with a three-way mirror and warm light.")],
}

MATERIALS_BY_STYLE = {
    "modern": [("Matte laminate", "#3A5560", "Anti-fingerprint, 1 mm"), ("Teak veneer", "#8A5F3F", "Natural, PU finish"), ("Quartz", "#E6E2DC", "Counter, 15 mm")],
    "contemporary": [("Oak veneer", "#B48A5E", "Smoked, matte"), ("Fluted panel", "#D8CDBE", "MDF, painted"), ("Brushed brass", "#B08D57", "Handles and trims")],
    "traditional": [("Sheesham wood", "#5E3A22", "Solid, hand-polished"), ("Brass inlay", "#B8862F", "Hand-crafted"), ("Kota stone", "#7D8471", "Leather finish")],
    "minimal": [("White oak", "#C9AE8A", "Natural oil"), ("Lime plaster", "#ECE6DC", "Hand-trowelled"), ("Linen", "#D9D2C5", "Upholstery")],
    "luxury": [("Italian marble", "#E7E1D8", "Statuario, polished"), ("Gold PVD", "#C9A55C", "Trims and handles"), ("Velvet", "#1F4D45", "Upholstery")],
}

COLOURS_BY_STYLE = {
    "modern": [("Deep teal", "#2F4A57"), ("Warm greige", "#D8D0C6"), ("Teak", "#8A5F3F"), ("Charcoal", "#2B2B2B")],
    "contemporary": [("Sage", "#7A8B6F"), ("Sand", "#E3D3BE"), ("Oak", "#9A6B44"), ("Brass", "#B08D57")],
    "traditional": [("Sindoor red", "#9B2D20"), ("Haldi", "#D9A441"), ("Sheesham", "#5E3A22"), ("Chandan", "#F1E2C8")],
    "minimal": [("Ivory", "#F4F2EE"), ("Stone", "#BFB6A8"), ("Oak", "#C2A27C"), ("Ink", "#3A3A3A")],
    "luxury": [("Charcoal", "#2E2C2B"), ("Emerald", "#1F4D45"), ("Gold", "#C7A86A"), ("Marble", "#E7E1D8")],
}

QUOTES = [
    "Every time someone visits, they ask who designed our home. That says it all.",
    "We approved designs from our phones while travelling. Nothing was lost in WhatsApp chats.",
    "The quotation matched the final bill. That almost never happens.",
]

# name, mobile, area/city, property, budget, mode, note — fictional people for upcoming bookings
BOOKING_PEOPLE = [
    ("Aditi Sharma", "9826011223", "Vijay Nagar, Indore", "2bhk", "5_10", "studio", "New 2BHK, possession next month."),
    ("Vikram Chouhan", "9893044556", "Saket Nagar, Indore", "3bhk", "10_20", "site_visit", "Full home interiors, want a modular kitchen too."),
    ("Neha Gupta", "9425077889", "Arera Colony, Bhopal", "3bhk", "10_20", "online", "Living and dining makeover before Diwali."),
    ("Rohan Malviya", "9977112233", "Nipania, Indore", "villa", "20_40", "site_visit", "Villa with 4 bedrooms and a home theatre."),
    ("Sneha Patel", "9300445566", "Palasia, Indore", "2bhk", "5_10", "studio", "Wardrobes and kids room."),
    ("Imran Qureshi", "9752233445", "MP Nagar, Bhopal", "office", "10_20", "online", "Office for 20 people."),
    ("Kavya Iyer", "9009988776", "Bicholi Mardana, Indore", "3bhk", "20_40", "studio", "Liked the Courtyard Home project."),
    ("Arjun Rathore", "9669900112", "Lashkar, Gwalior", "4bhk", "20_40", "online", "Traditional style, joint family."),
    ("Pooja Jain", "9584433221", "Rau, Indore", "1bhk", "under_5", "studio", "Rental flat refresh on a budget."),
    ("Siddharth Verma", "9826543210", "Scheme 78, Indore", "retail", "10_20", "site_visit", "Showroom for ethnic wear."),
    ("Ritu Saxena", "9893123987", "Kolar Road, Bhopal", "2bhk", "5_10", "online", "Modular kitchen only."),
    ("Manish Agrawal", "9425098765", "Sudama Nagar, Indore", "3bhk", "10_20", "studio", "Renovation of a 15-year-old flat."),
]

# 45 more portfolio designs (core/demo_more_designs.py) so the website shows a fuller catalogue.
from core.demo_more_designs import MORE_PROJECTS  # noqa: E402

PROJECTS = PROJECTS + MORE_PROJECTS
