"""Tasteful, offline-generated interior illustrations for the demo (Pillow only).

Each image is a stylised room render: lit wall gradient, floor with planks/tiles,
window light, and furniture appropriate to the room type, tinted by a style palette.
"Before" images are the same room empty, dull and unfinished.
"""
import io
import random

from PIL import Image, ImageDraw, ImageFilter

W, H = 1400, 933

PALETTES = {
    "modern":       {"wall": ("#E9E4DD", "#D8D0C6"), "floor": "#B48A64", "accent": "#2F4A57", "soft": "#C9B8A5", "wood": "#8A5F3F", "metal": "#2B2B2B"},
    "contemporary": {"wall": ("#EDE6DA", "#DCCFBE"), "floor": "#C49A6C", "accent": "#7A8B6F", "soft": "#E3D3BE", "wood": "#9A6B44", "metal": "#B08D57"},
    "traditional":  {"wall": ("#F1E2C8", "#E1C79F"), "floor": "#8E5B3A", "accent": "#9B2D20", "soft": "#D9A441", "wood": "#5E3A22", "metal": "#B8862F"},
    "minimal":      {"wall": ("#F4F2EE", "#E6E2DB"), "floor": "#D6C3A5", "accent": "#BFB6A8", "soft": "#ECE6DC", "wood": "#C2A27C", "metal": "#3A3A3A"},
    "luxury":       {"wall": ("#2E2C2B", "#4A4542"), "floor": "#E7E1D8", "accent": "#1F4D45", "soft": "#C7A86A", "wood": "#4A2F22", "metal": "#C9A55C"},
}


def _hex(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _mix(a, b, t):
    a, b = _hex(a) if isinstance(a, str) else a, _hex(b) if isinstance(b, str) else b
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _shade(c, f):
    c = _hex(c) if isinstance(c, str) else c
    return tuple(max(0, min(255, int(v * f))) for v in c)


def _vgradient(draw, box, top, bottom):
    x0, y0, x1, y1 = box
    for y in range(int(y0), int(y1)):
        t = (y - y0) / max(1, (y1 - y0))
        draw.line([(x0, y), (x1, y)], fill=_mix(top, bottom, t))


def _shell(d, pal, rnd, empty=False, floor_y=None):
    floor_y = floor_y or int(H * rnd.uniform(.66, .72))
    wall_top, wall_bottom = pal["wall"]
    if empty:
        wall_top, wall_bottom = "#C9C5BE", "#B3AEA6"
    _vgradient(d, (0, 0, W, floor_y), wall_top, wall_bottom)
    # skirting / floor
    floor = "#9C958C" if empty else pal["floor"]
    _vgradient(d, (0, floor_y, W, H), _shade(floor, 1.05), _shade(floor, .82))
    if empty:
        for x in range(0, W, 140):  # rough screed patches
            d.line([(x + rnd.randint(-20, 20), floor_y), (x + rnd.randint(-60, 60), H)], fill=_shade(floor, .9), width=2)
    else:
        for i in range(1, 9):  # perspective planks
            y = floor_y + (H - floor_y) * (i / 9) ** 1.4
            d.line([(0, y), (W, y)], fill=_shade(floor, .9), width=1)
        for x in range(-W, 2 * W, 120):
            d.line([(W / 2 + (x - W / 2) * .35, floor_y), (x, H)], fill=_shade(floor, .93), width=1)
    d.rectangle([0, floor_y - 10, W, floor_y], fill=_shade(wall_bottom, .85))
    return floor_y


def _window(d, pal, x, y, w, h, empty=False):
    frame = (235, 235, 230) if not empty else (170, 168, 160)
    glass_top, glass_bottom = ((206, 225, 236), (244, 238, 222)) if not empty else ((190, 196, 198), (210, 208, 200))
    d.rectangle([x - 8, y - 8, x + w + 8, y + h + 8], fill=frame)
    _vgradient(d, (x, y, x + w, y + h), glass_top, glass_bottom)
    d.line([(x + w / 2, y), (x + w / 2, y + h)], fill=frame, width=6)
    d.line([(x, y + h * .38), (x + w, y + h * .38)], fill=frame, width=5)
    if not empty:  # sheer curtains
        for cx in (x - 30, x + w - 10):
            d.rectangle([cx, y - 30, cx + 40, y + h + 60], fill=_mix(pal["soft"], "#FFFFFF", .55))


def _light_glow(img, cx, cy, r, strength=70):
    glow = Image.new("L", img.size, 0)
    gd = ImageDraw.Draw(glow)
    for i in range(12, 0, -1):
        rr = r * i / 12
        gd.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=int(strength * (1 - i / 13)))
    glow = glow.filter(ImageFilter.GaussianBlur(r / 4))
    warm = Image.new("RGB", img.size, (255, 236, 200))
    return Image.composite(warm, img, glow)


def _rug(d, pal, cx, cy, w, h):
    d.ellipse([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], fill=_mix(pal["soft"], "#FFFFFF", .25))
    d.ellipse([cx - w / 2 + 18, cy - h / 2 + 8, cx + w / 2 - 18, cy + h / 2 - 8], outline=_shade(pal["soft"], .85), width=3)


def _plant(d, x, base_y, rnd, scale=1.0):
    pot = (196, 160, 120)
    d.rounded_rectangle([x - 28 * scale, base_y - 70 * scale, x + 28 * scale, base_y], radius=10, fill=pot)
    for _ in range(14):
        ang_x = rnd.uniform(-90, 90) * scale
        top = base_y - rnd.uniform(160, 260) * scale
        d.ellipse([x + ang_x - 22 * scale, top, x + ang_x + 22 * scale, top + 70 * scale],
                  fill=_mix((60, 110, 70), (110, 150, 90), rnd.random()))
        d.line([(x, base_y - 60 * scale), (x + ang_x, top + 40 * scale)], fill=(70, 100, 60), width=3)


def _art(d, pal, x, y, w, h, rnd):
    d.rectangle([x - 6, y - 6, x + w + 6, y + h + 6], fill=pal["metal"])
    d.rectangle([x, y, x + w, y + h], fill=_mix(pal["wall"][0], "#FFFFFF", .5))
    for _ in range(3):
        cx, cy, r = x + rnd.uniform(.2, .8) * w, y + rnd.uniform(.2, .8) * h, rnd.uniform(.12, .3) * min(w, h)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=rnd.choice([pal["accent"], pal["soft"], pal["wood"]]))


def _pendant(d, pal, x, ceiling, drop, size=40):
    d.line([(x, ceiling), (x, ceiling + drop)], fill=pal["metal"], width=2)
    d.pieslice([x - size, ceiling + drop - 4, x + size, ceiling + drop + size * 1.4], 180, 360, fill=pal["metal"])


def _living(img, d, pal, rnd, fy):
    _window(d, pal, 90, 140, 300, int(fy - 260))
    _art(d, pal, 640, 170, 220, 160, rnd)
    _art(d, pal, 890, 200, 130, 130, rnd)
    _rug(d, pal, W * .55, fy + 150, 900, 170)
    # sofa
    sx, sy, sw = 470, fy - 40, 640
    d.rounded_rectangle([sx, sy - 190, sx + sw, sy - 60], radius=28, fill=_shade(pal["accent"], .9))
    d.rounded_rectangle([sx - 30, sy - 110, sx + sw + 30, sy + 10], radius=26, fill=pal["accent"])
    for i in range(3):
        cx = sx + 40 + i * (sw - 80) / 3
        d.rounded_rectangle([cx, sy - 108, cx + (sw - 80) / 3 - 12, sy - 40], radius=18, fill=_shade(pal["accent"], 1.12))
    for px in (sx + 70, sx + sw - 140):
        d.rounded_rectangle([px, sy - 170, px + 80, sy - 105], radius=14, fill=pal["soft"])
    d.rectangle([sx - 10, sy + 10, sx + 4, sy + 34], fill=pal["metal"])
    d.rectangle([sx + sw - 4, sy + 10, sx + sw + 10, sy + 34], fill=pal["metal"])
    # coffee table
    d.ellipse([W * .55 - 180, fy + 95, W * .55 + 180, fy + 155], fill=pal["wood"])
    d.rectangle([W * .55 - 6, fy + 125, W * .55 + 6, fy + 190], fill=_shade(pal["wood"], .7))
    # floor lamp + plant
    d.line([(1220, fy + 20), (1220, fy - 300)], fill=pal["metal"], width=5)
    d.pieslice([1160, fy - 340, 1280, fy - 250], 180, 360, fill=pal["soft"])
    _plant(d, 380, fy + 30, rnd)
    return _light_glow(img, 1220, fy - 290, 260, 80)


def _bedroom(img, d, pal, rnd, fy):
    _window(d, pal, 1030, 150, 260, int(fy - 270))
    cx = 600
    d.rounded_rectangle([cx - 330, fy - 330, cx + 330, fy - 60], radius=20, fill=pal["soft"])  # headboard panel
    for i in range(6):
        x = cx - 330 + i * 110
        d.line([(x, fy - 330), (x, fy - 60)], fill=_shade(pal["soft"], .9), width=2)
    d.rounded_rectangle([cx - 300, fy - 120, cx + 300, fy + 70], radius=18, fill=(246, 243, 238))
    d.rounded_rectangle([cx - 300, fy - 30, cx + 300, fy + 70], radius=18, fill=pal["accent"])
    for px in (cx - 250, cx + 30):
        d.rounded_rectangle([px, fy - 170, px + 220, fy - 100], radius=22, fill=(252, 250, 246))
    d.rounded_rectangle([cx - 90, fy - 150, cx + 90, fy - 95], radius=16, fill=pal["soft"])
    for sx in (cx - 450, cx + 340):
        d.rectangle([sx, fy - 90, sx + 110, fy + 20], fill=pal["wood"])
        d.line([(sx, fy - 35), (sx + 110, fy - 35)], fill=_shade(pal["wood"], .8), width=2)
    _pendant(d, pal, cx - 395, 0, fy - 250, 30)
    _pendant(d, pal, cx + 395, 0, fy - 250, 30)
    _rug(d, pal, cx, fy + 160, 900, 140)
    img = _light_glow(img, cx - 395, fy - 220, 160, 70)
    return _light_glow(img, cx + 395, fy - 220, 160, 70)


def _kitchen(img, d, pal, rnd, fy):
    top = fy - 210
    d.rectangle([0, top - 200, W, top], fill=_mix(pal["wall"][0], "#FFFFFF", .3))  # backsplash
    for x in range(0, W, 60):
        d.line([(x, top - 200), (x, top)], fill=_shade(pal["wall"][0], .93))
    for y in range(int(top - 200), int(top), 30):
        d.line([(0, y), (W, y)], fill=_shade(pal["wall"][0], .93))
    # upper cabinets
    for x in range(40, W - 300, 170):
        d.rectangle([x, 70, x + 160, top - 230], fill=pal["soft"])
        d.line([(x + 140, top - 300), (x + 140, top - 250)], fill=pal["metal"], width=4)
    _window(d, pal, W - 260, 90, 200, int(top - 330))
    # counter + base cabinets
    d.rectangle([0, top, W, top + 22], fill=(236, 232, 226))
    for x in range(0, W, 175):
        d.rectangle([x + 4, top + 26, x + 170, fy + 10], fill=pal["accent"])
        d.line([(x + 30, top + 60), (x + 140, top + 60)], fill=pal["metal"], width=4)
    # hob + hood
    d.rectangle([560, top - 6, 760, top], fill=(30, 30, 30))
    d.polygon([(590, top - 360), (730, top - 360), (760, top - 250), (560, top - 250)], fill=pal["metal"])
    # island
    d.rectangle([380, fy + 60, 1020, fy + 84], fill=(240, 236, 230))
    d.rectangle([400, fy + 84, 1000, H], fill=pal["wood"])
    for bx in (480, 700, 920):
        _pendant(d, pal, bx, 0, fy - 120, 34)
    _plant(d, 1120, top, rnd, .45)
    for bx in (480, 700, 920):
        img = _light_glow(img, bx, fy - 90, 140, 60)
    return img


def _office(img, d, pal, rnd, fy):
    _window(d, pal, 80, 120, 520, int(fy - 230))
    for i in range(4):  # shelves
        y = 150 + i * 100
        d.rectangle([860, y, 1300, y + 12], fill=pal["wood"])
        for j in range(rnd.randint(4, 8)):
            bx = 870 + j * 50 + rnd.randint(0, 10)
            d.rectangle([bx, y - rnd.randint(50, 80), bx + 32, y], fill=rnd.choice([pal["accent"], pal["soft"], pal["metal"], pal["wood"]]))
    d.rectangle([420, fy - 70, 1000, fy - 46], fill=pal["wood"])
    d.rectangle([440, fy - 46, 460, fy + 70], fill=pal["metal"])
    d.rectangle([960, fy - 46, 980, fy + 70], fill=pal["metal"])
    d.rectangle([620, fy - 230, 820, fy - 100], fill=(30, 32, 36))
    d.rectangle([700, fy - 100, 740, fy - 70], fill=pal["metal"])
    d.rounded_rectangle([640, fy - 30, 800, fy + 110], radius=24, fill=pal["accent"])
    d.rounded_rectangle([650, fy - 160, 790, fy - 20], radius=24, fill=_shade(pal["accent"], .85))
    _plant(d, 1230, fy + 40, rnd, .9)
    return _light_glow(img, 330, 300, 380, 60)


def _retail(img, d, pal, rnd, fy):
    for side in (0, 1):
        x0 = 60 if side == 0 else W - 420
        for i in range(4):
            y = 150 + i * 120
            d.rectangle([x0, y, x0 + 360, y + 10], fill=pal["metal"])
            for j in range(6):
                bx = x0 + 10 + j * 58
                d.rounded_rectangle([bx, y - 80, bx + 44, y], radius=6, fill=rnd.choice([pal["accent"], pal["soft"], pal["wood"], (230, 225, 218)]))
    d.rectangle([520, fy - 40, 880, fy + 80], fill=pal["wood"])
    d.rectangle([500, fy - 60, 900, fy - 40], fill=(240, 236, 230))
    for j in range(5):
        d.rounded_rectangle([540 + j * 68, fy - 120, 590 + j * 68, fy - 60], radius=8, fill=rnd.choice([pal["accent"], pal["soft"]]))
    for bx in (560, 700, 840):
        _pendant(d, pal, bx, 0, fy - 330, 30)
    return _light_glow(img, 700, fy - 260, 320, 70)


ROOM_DRAWERS = {
    "living": _living, "full_home": _living, "bedroom": _bedroom,
    "kitchen": _kitchen, "office": _office, "retail": _retail,
}


def _finish(img, rnd):
    img = img.filter(ImageFilter.GaussianBlur(.8))
    # vignette
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).ellipse([-W * .15, -H * .2, W * 1.15, H * 1.2], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(120))
    dark = Image.new("RGB", img.size, (30, 24, 20))
    return Image.composite(img, Image.blend(img, dark, .35), mask)


def room_image(style, room_type, seed, empty=False):
    rnd = random.Random(seed)
    pal = dict(PALETTES.get(style, PALETTES["modern"]))
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    fy = _shell(d, pal, rnd, empty=empty)
    if empty:
        _window(d, pal, rnd.choice([120, 900]), 150, 320, int(fy - 270), empty=True)
        d.line([(W / 2, 0), (W / 2, 80)], fill=(60, 60, 60), width=2)
        d.ellipse([W / 2 - 10, 78, W / 2 + 10, 100], fill=(250, 240, 200))
        for _ in range(4):  # patchy walls / cables
            x, y = rnd.randint(100, W - 200), rnd.randint(80, int(fy) - 200)
            d.rectangle([x, y, x + rnd.randint(60, 180), y + rnd.randint(40, 120)], fill=(184, 180, 172))
        d.rectangle([W - 300, fy - 30, W - 180, fy + 40], fill=(150, 140, 120))  # cement bags
        img = img.filter(ImageFilter.GaussianBlur(.8))
        return img
    drawer = ROOM_DRAWERS.get(room_type, _living)
    img = drawer(img, d, pal, rnd, fy) or img
    return _finish(img, rnd)


def to_jpeg_bytes(img, quality=80):
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=quality, optimize=True, progressive=True)
    return buf.getvalue()


def to_thumb(img, width=900):
    h = int(img.height * width / img.width)
    return img.resize((width, h), Image.LANCZOS)
