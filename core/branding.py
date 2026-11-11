"""Pick brand colours from a logo (for brand_demo) — no extra packages, just Pillow + colorsys."""
import colorsys

from PIL import Image

DEFAULT = ("#0081F6", "#2474F8", "#111212")


def _hex(rgb):
    return "#{:02X}{:02X}{:02X}".format(*(max(0, min(255, round(c))) for c in rgb))


def _luminance(rgb):
    def ch(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_with_white(rgb):
    return 1.05 / (_luminance(rgb) + 0.05)


def _from_hls(h, l, s):
    return tuple(c * 255 for c in colorsys.hls_to_rgb(h, l, s))


def palette_from_logo(path_or_file):
    """Return (primary, secondary, dark) hex colours. Falls back to the default blue for grey/mono logos."""
    try:
        img = Image.open(path_or_file).convert("RGBA")
    except Exception:
        return DEFAULT
    img.thumbnail((96, 96))
    counts = {}
    for r, g, b, a in img.getdata():
        if a < 128:
            continue
        h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        if s < 0.25 or l < 0.12 or l > 0.92:       # skip white, black and greys
            continue
        key = (round(h * 24) % 24, round(l * 6))  # bucket similar shades together
        bucket = counts.setdefault(key, [0, 0, 0, 0])
        bucket[0] += 1
        bucket[1] += r
        bucket[2] += g
        bucket[3] += b
    if not counts:
        return DEFAULT
    n, r, g, b = max(counts.values(), key=lambda v: v[0])
    if n < 12:                                    # a few stray coloured pixels are not a brand colour
        return DEFAULT
    h, l, s = colorsys.rgb_to_hls(r / n / 255, g / n / 255, b / n / 255)
    s = max(s, 0.45)
    primary = _from_hls(h, l, s)
    while contrast_with_white(primary) < 3.2 and l > 0.15:   # buttons must stay readable with white text
        l -= 0.03
        primary = _from_hls(h, l, s)
    secondary = _from_hls((h + 0.02) % 1, min(l + 0.08, 0.6), min(s + 0.05, 1))
    dark = _from_hls(h, 0.08, min(s, 0.35))
    return _hex(primary), _hex(secondary), _hex(dark)
