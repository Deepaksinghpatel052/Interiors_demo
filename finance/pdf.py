"""Branded quotation / invoice PDFs with xhtml2pdf. Uses bundled Noto Sans so ₹ renders correctly."""
import io
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from xhtml2pdf import pisa

from core.models import StudioSettings

from .models import money
from .services import amount_in_words, schedule_split

FONT_DIR = Path(settings.BASE_DIR) / "static" / "fonts"


def _link_callback(uri, rel):
    """Only allow files from our own static/media folders (never fetch remote URLs)."""
    if uri.startswith(settings.MEDIA_URL):
        path = Path(settings.MEDIA_ROOT) / uri[len(settings.MEDIA_URL):]
    elif uri.startswith("/" + settings.STATIC_URL.lstrip("/")):
        path = Path(settings.BASE_DIR) / "static" / uri[len("/" + settings.STATIC_URL.lstrip("/")):]
    else:
        path = Path(uri)
    try:
        path = path.resolve()
        allowed = [Path(settings.MEDIA_ROOT).resolve(), (Path(settings.BASE_DIR) / "static").resolve()]
        if any(str(path).startswith(str(a)) for a in allowed) and path.exists():
            return str(path)
    except OSError:
        pass
    return ""


def render_pdf(template, context, filename, inline=True):
    s = StudioSettings.load()
    fonts = {w: (FONT_DIR / f"NotoSans-{w}.ttf").as_posix() for w in ("Regular", "SemiBold", "Bold")}
    ctx = {
        "studio": s,
        "fonts": fonts,
        "has_font": all(Path(p).exists() for p in fonts.values()),
        "logo_path": s.logo.path if s.logo and Path(s.logo.path).exists() else "",
        **context,
    }
    ctx["rupee"] = "₹" if ctx["has_font"] else "Rs."
    html = render_to_string(template, ctx)
    out = io.BytesIO()
    result = pisa.CreatePDF(html, dest=out, link_callback=_link_callback, encoding="utf-8")
    if result.err:
        return HttpResponse("Could not generate the PDF.", status=500)
    resp = HttpResponse(out.getvalue(), content_type="application/pdf")
    resp["Content-Disposition"] = f'{"inline" if inline else "attachment"}; filename="{filename}"'
    return resp


def quotation_pdf(q, inline=True):
    rooms = list(q.rooms.prefetch_related("items"))
    return render_pdf("finance/pdf/quotation.html", {
        "q": q, "rooms": rooms, "words": amount_in_words(q.grand_total),
        "breakdown": [(rate, taxable, gst, money(gst / 2), gst - money(gst / 2)) for rate, taxable, gst in q.gst_breakdown()],
        "terms_lines": [t for t in (q.terms or "").splitlines() if t.strip()],
        "schedule": [(s.label, s.percent, s.amount) for s in q.schedule.all()] or schedule_split(q.grand_total),
    }, f"{q.display_number.replace('/', '-').replace(' ', '')}.pdf", inline)


def invoice_pdf(inv, inline=True):
    return render_pdf("finance/pdf/invoice.html", {
        "inv": inv, "payments": list(inv.payments.all()), "words": amount_in_words(inv.total),
    }, f"{inv.number.replace('/', '-')}.pdf", inline)
