"""Roles: Owner (full access), Team Member (day-to-day work), Client (portal only)."""
from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

OWNER, TEAM, CLIENT = "Owner", "Team Member", "Client"


def _groups(user):
    if not hasattr(user, "_group_names"):
        user._group_names = set(user.groups.values_list("name", flat=True))
    return user._group_names


def is_owner(user):
    return user.is_authenticated and (user.is_superuser or OWNER in _groups(user))


def is_team(user):
    """Anyone who works in the studio (owner or team member)."""
    return user.is_authenticated and (is_owner(user) or TEAM in _groups(user))


def is_client(user):
    return user.is_authenticated and CLIENT in _groups(user) and not is_team(user)


def role_of(user):
    if is_owner(user):
        return "owner"
    if is_team(user):
        return "team"
    if is_client(user):
        return "client"
    return "visitor"


def _require(check):
    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if not check(request.user):
                raise PermissionDenied
            return view(request, *args, **kwargs)
        return wrapper
    return decorator


team_required = _require(is_team)
owner_required = _require(is_owner)
client_required = _require(is_client)
