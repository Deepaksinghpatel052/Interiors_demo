"""Cost estimator — an indicative range only. Rates per finish level come from StudioSettings
(editable in the ERP/admin), so no prices are hard-coded here."""
from decimal import ROUND_HALF_UP, Decimal

PROPERTY_TYPES = [
    ("1bhk", "1 BHK"), ("2bhk", "2 BHK"), ("3bhk", "3 BHK"), ("villa", "Villa"), ("office", "Office"),
]

# Typical carpet area (sq ft) per room, used to suggest the area. Visitors can edit the total.
ROOMS = {
    "living": ("Living room", 220),
    "dining": ("Dining", 120),
    "kitchen": ("Kitchen", 100),
    "master_bedroom": ("Master bedroom", 180),
    "bedroom": ("Other bedroom", 140),
    "kids_room": ("Kids' room", 130),
    "pooja": ("Pooja room", 25),
    "study": ("Study / home office", 90),
    "balcony": ("Balcony", 60),
    "workstations": ("Workstations", 600),
    "cabins": ("Cabins", 240),
    "reception": ("Reception & waiting", 200),
    "conference": ("Conference room", 220),
}

DEFAULT_ROOMS = {
    "1bhk": ["living", "kitchen", "master_bedroom"],
    "2bhk": ["living", "dining", "kitchen", "master_bedroom", "bedroom"],
    "3bhk": ["living", "dining", "kitchen", "master_bedroom", "bedroom", "kids_room", "pooja"],
    "villa": ["living", "dining", "kitchen", "master_bedroom", "bedroom", "kids_room", "pooja", "study", "balcony"],
    "office": ["workstations", "cabins", "reception", "conference"],
}

FINISHES = [
    ("essential", "Essential", "Good-quality laminates, MR plywood, standard hardware."),
    ("premium", "Premium", "Premium laminates/veneer, BWP plywood in wet areas, soft-close hardware."),
    ("luxury", "Luxury", "Veneers, lacquer, quartz/marble, imported hardware and decorative lighting."),
]

LOW_FACTOR = Decimal("0.90")
HIGH_FACTOR = Decimal("1.15")
MIN_AREA, MAX_AREA = 50, 20000


def suggested_area(rooms):
    return sum(ROOMS[r][1] for r in rooms if r in ROOMS)


def _round_to(value, step=10000):
    return int((Decimal(value) / step).quantize(Decimal(1), rounding=ROUND_HALF_UP) * step)


def calculate(property_type, rooms, finish, area, studio):
    """Return the indicative range. Raises ValueError for invalid input."""
    if property_type not in dict(PROPERTY_TYPES):
        raise ValueError("Choose a property type.")
    rooms = [r for r in rooms if r in ROOMS]
    if not rooms:
        raise ValueError("Choose at least one room.")
    rates = {"essential": studio.rate_essential, "premium": studio.rate_premium, "luxury": studio.rate_luxury}
    if finish not in rates:
        raise ValueError("Choose a finish level.")
    try:
        area = int(area)
    except (TypeError, ValueError):
        raise ValueError("Enter the carpet area in sq ft.")
    if not MIN_AREA <= area <= MAX_AREA:
        raise ValueError(f"Area should be between {MIN_AREA} and {MAX_AREA:,} sq ft.")
    rate = Decimal(rates[finish])
    base = rate * area
    return {
        "property_type": property_type,
        "property_label": dict(PROPERTY_TYPES)[property_type],
        "rooms": rooms,
        "room_labels": [ROOMS[r][0] for r in rooms],
        "finish": finish,
        "finish_label": dict((f[0], f[1]) for f in FINISHES)[finish],
        "area": area,
        "rate": int(rate),
        "low": _round_to(base * LOW_FACTOR),
        "high": _round_to(base * HIGH_FACTOR),
    }
