"""Small fixed-window rate limiter on Django's cache."""
from django.core.cache import cache


def hit(key: str, limit: int, window_seconds: int) -> bool:
    """Count one request for `key`; return True if it is within the limit."""
    cache_key = f"rl:{key}"
    if cache.add(cache_key, 1, window_seconds):
        return True
    try:
        count = cache.incr(cache_key)
    except ValueError:  # expired between add and incr
        cache.set(cache_key, 1, window_seconds)
        return True
    return count <= limit


def client_ip(request) -> str:
    # X-Forwarded-For is never trusted. X-Real-IP only when TRUST_X_REAL_IP is on, i.e. the app port is
    # reachable from the server's own nginx alone, which overwrites the header with the real address.
    from django.conf import settings
    if getattr(settings, "TRUST_X_REAL_IP", False):
        real = request.META.get("HTTP_X_REAL_IP", "").strip()
        if real:
            return real
    return request.META.get("REMOTE_ADDR", "") or "unknown"
