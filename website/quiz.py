"""Style quiz: 5 picture-based questions. Each option points at one style.
Pictures are portfolio images of that style (so a rebranded studio's own photos appear)
with colour/material swatches as the visual for the palette questions."""
from collections import Counter

from .models import PortfolioProject, ProjectImage, Style

STYLE_ORDER = [s for s in Style.values]

QUESTIONS = [
    {"key": "living", "title": "Which living room would you relax in?", "kind": "image", "room": ["living", "full_home"]},
    {"key": "palette", "title": "Pick the colours that feel like home.", "kind": "palette"},
    {"key": "bedroom", "title": "Which bedroom feels most restful?", "kind": "image", "room": ["bedroom"]},
    {"key": "material", "title": "Which materials would you love to touch every day?", "kind": "material"},
    {"key": "kitchen", "title": "And the kitchen — which one is you?", "kind": "image", "room": ["kitchen"]},
]

PALETTES = {
    "modern": ["#2F4A57", "#D8D0C6", "#8A5F3F", "#2B2B2B"],
    "contemporary": ["#7A8B6F", "#E3D3BE", "#9A6B44", "#B08D57"],
    "traditional": ["#9B2D20", "#D9A441", "#5E3A22", "#F1E2C8"],
    "minimal": ["#F4F2EE", "#BFB6A8", "#C2A27C", "#3A3A3A"],
    "luxury": ["#2E2C2B", "#1F4D45", "#C7A86A", "#E7E1D8"],
}

MATERIALS = {
    "modern": [("Matte laminate", "#3A5560"), ("Teak", "#8A5F3F"), ("Quartz", "#E6E2DC")],
    "contemporary": [("Oak veneer", "#B48A5E"), ("Fluted panel", "#D8CDBE"), ("Brushed brass", "#B08D57")],
    "traditional": [("Sheesham", "#5E3A22"), ("Brass inlay", "#B8862F"), ("Kota stone", "#7D8471")],
    "minimal": [("White oak", "#C9AE8A"), ("Lime plaster", "#ECE6DC"), ("Linen", "#D9D2C5")],
    "luxury": [("Marble", "#E7E1D8"), ("Gold PVD", "#C9A55C"), ("Velvet", "#1F4D45")],
}

DESCRIPTIONS = {
    "modern": "Clean lines, a few bold colours and warm wood. Practical, uncluttered and easy to live with.",
    "contemporary": "Soft, natural tones with texture — fluted panels, oak and brass. Current without being cold.",
    "traditional": "Rich colours, carved wood, brass and stone. Rooted in Indian craft, designed for family and festivals.",
    "minimal": "Light, calm and quiet. Hidden storage, natural materials and lots of breathing space.",
    "luxury": "Deep colours, marble and metallic accents. Dramatic spaces made for hosting and celebrating.",
}


def _image_for(style, rooms):
    img = (ProjectImage.objects.filter(project__is_published=True, project__style=style, room__in=rooms)
           .order_by("order").first())
    if img:
        return img.image.url
    p = PortfolioProject.objects.filter(is_published=True, style=style, room_type__in=rooms).first()
    # No photo of this room in this style: the caller falls back to the style's colour palette
    # rather than showing an unrelated room.
    return p.cover.url if p else ""


def build_questions():
    out = []
    for q in QUESTIONS:
        options = []
        for style in STYLE_ORDER:
            opt = {"style": style}
            if q["kind"] == "image":
                opt["image"] = _image_for(style, q["room"])
                if not opt["image"]:
                    opt["colours"] = PALETTES[style]
            elif q["kind"] == "palette":
                opt["colours"] = PALETTES[style]
            else:
                opt["materials"] = MATERIALS[style]
            options.append(opt)
        # Show options in a different order for each question so the pattern isn't obvious.
        shift = len(out) * 2 % len(options)
        out.append({**q, "options": options[shift:] + options[:shift]})
    return out


def score(answers):
    """answers: list of style keys. Returns the winning style (ties → earliest answer wins)."""
    valid = [a for a in answers if a in STYLE_ORDER]
    if not valid:
        return None
    counts = Counter(valid)
    best = max(counts.values())
    for a in valid:  # earliest answer among the tied styles
        if counts[a] == best:
            return a
