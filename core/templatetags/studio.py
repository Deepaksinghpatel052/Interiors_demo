"""Template helpers for Indian formats and WhatsApp links. Loaded as a builtin."""
from decimal import Decimal, InvalidOperation
from urllib.parse import quote

from django import template

register = template.Library()


def _indian_group(int_str: str) -> str:
    """'12500000' -> '1,25,00,000'."""
    if len(int_str) <= 3:
        return int_str
    head, tail = int_str[:-3], int_str[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return ",".join(groups) + "," + tail


def format_inr(value, decimals=0, symbol=True):
    try:
        amount = Decimal(str(value if value not in (None, "") else 0))
    except (InvalidOperation, ValueError):
        return value
    negative = amount < 0
    amount = abs(amount).quantize(Decimal(1) if decimals == 0 else Decimal("0.01"))
    int_part, _, frac = f"{amount:.{decimals}f}".partition(".")
    out = _indian_group(int_part) + (f".{frac}" if decimals else "")
    out = ("₹" if symbol else "") + out
    return "−" + out if negative else out


@register.filter
def inr(value):
    """₹1,25,000"""
    return format_inr(value)


@register.filter
def inr2(value):
    """₹1,25,000.50"""
    return format_inr(value, decimals=2)


@register.filter
def inr_short(value):
    """₹4.5L / ₹1.2Cr — for compact KPI cards."""
    try:
        v = float(value or 0)
    except (TypeError, ValueError):
        return value
    if v >= 1e7:
        return f"₹{v / 1e7:.1f}Cr".replace(".0Cr", "Cr")
    if v >= 1e5:
        return f"₹{v / 1e5:.1f}L".replace(".0L", "L")
    return format_inr(v)


@register.simple_tag
def wa_link(number, text=""):
    digits = "".join(c for c in str(number or "") if c.isdigit())
    url = f"https://wa.me/{digits}"
    if text:
        url += "?text=" + quote(text)
    return url


@register.filter
def tel(number):
    return "tel:" + "".join(c for c in str(number or "") if c.isdigit() or c == "+")


@register.filter
def split_lines(value):
    return [line.strip() for line in str(value or "").splitlines() if line.strip()]


@register.simple_tag(takes_context=True)
def active(context, *url_names):
    match = getattr(context.get("request"), "resolver_match", None)
    if match and (match.view_name in url_names or match.url_name in url_names):
        return "active"
    return ""


@register.simple_tag(takes_context=True)
def query_replace(context, **kwargs):
    """Build a querystring keeping current GET params (for filter links)."""
    params = context["request"].GET.copy()
    for k, v in kwargs.items():
        if v in (None, ""):
            params.pop(k, None)
        else:
            params[k] = v
    qs = params.urlencode()
    return f"?{qs}" if qs else "?"


@register.filter
def num(value):
    """Indian digit grouping without the ₹ symbol: 1,25,000"""
    return format_inr(value, symbol=False)


@register.filter
def india(number):
    """10-digit Indian mobile -> 91XXXXXXXXXX for wa.me / tel links."""
    digits = "".join(c for c in str(number or "") if c.isdigit())
    return "91" + digits if len(digits) == 10 else digits


@register.filter
def pdf_money(value, symbol="₹"):
    """Indian grouping with 2 decimals for PDFs (symbol passed in, since fonts differ)."""
    text = format_inr(value, decimals=2, symbol=False)
    return f"−{symbol}{text[1:]}" if str(text).startswith("−") else f"{symbol}{text}"


@register.filter
def pct(value):
    """18.00 -> 18, 12.50 -> 12.5"""
    try:
        return f"{float(value):g}"
    except (TypeError, ValueError):
        return value


@register.filter
def split(value, sep="|"):
    """'a|b|c' -> ['a', 'b', 'c'] (used for short lists written inline in templates)."""
    return [part.strip() for part in str(value or "").split(sep) if part.strip()]
