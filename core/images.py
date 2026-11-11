"""Resize + compress uploaded photos so pages stay fast on 4G (used by the CMS and brand_demo)."""
import io
import os

from django.core.files.base import ContentFile
from PIL import Image, ImageOps


def optimise(fileobj, name=None, max_px=1800, quality=82):
    """Return a ContentFile JPEG (or PNG when the image has transparency), longest side <= max_px."""
    img = Image.open(fileobj)
    img = ImageOps.exif_transpose(img)
    has_alpha = img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)
    img.thumbnail((max_px, max_px), Image.LANCZOS)
    buf = io.BytesIO()
    base = os.path.splitext(os.path.basename(name or getattr(fileobj, "name", "") or "photo"))[0][:60] or "photo"
    if has_alpha:
        img.convert("RGBA").save(buf, "PNG", optimize=True)
        ext = "png"
    else:
        img.convert("RGB").save(buf, "JPEG", quality=quality, optimize=True, progressive=True)
        ext = "jpg"
    return ContentFile(buf.getvalue(), name=f"{base}.{ext}")
