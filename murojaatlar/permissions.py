"""
Centralised access control.

Every view-level role check should go through these helpers so adding a new
role or tweaking the permission matrix is a single-file change.
"""
from __future__ import annotations

from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from .models import Role


def role_of(user) -> str:
    """Return the user's role string, defaulting to 'hodim' for safety.

    A safe fallback matters: if the profile signal hasn't fired yet (very
    fresh row, race), we want the *least* privileged behaviour — not a crash.
    """
    if not user.is_authenticated:
        return ''
    profile = getattr(user, 'profile', None)
    return profile.role if profile is not None else Role.HODIM


def can_view(user) -> bool:
    return user.is_authenticated


def can_edit(user) -> bool:
    return role_of(user) in {Role.ADMIN, Role.IMAM}


def is_admin(user) -> bool:
    return role_of(user) == Role.ADMIN


# ─── Decorators ────────────────────────────────────────────────────────────────

def _redirect_with_message(request, text, fallback='dashboard'):
    messages.error(request, text)
    next_url = request.META.get('HTTP_REFERER')
    return redirect(next_url) if next_url else redirect(fallback)


def admin_required(view_func):
    """Allow only the admin role. Imam/hodim get an explicit error."""

    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not is_admin(request.user):
            return _redirect_with_message(
                request, "Faqat administrator bu amalni bajara oladi."
            )
        return view_func(request, *args, **kwargs)

    return _wrapped


def can_edit_required(view_func):
    """Allow admin and imam (the editing roles)."""

    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not can_edit(request.user):
            return _redirect_with_message(
                request, "Sizda bu amalni bajarish huquqi yo'q."
            )
        return view_func(request, *args, **kwargs)

    return _wrapped
