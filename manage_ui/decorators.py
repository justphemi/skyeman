"""Decorators for the Skyeman operations console."""
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib import messages


def staff_required(view_func):
    """Allow only authenticated staff users; redirect others with a friendly message."""
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, "Staff credentials required to access the operations console.")
            return redirect("dropzones:home")
        return view_func(request, *args, **kwargs)
    return _wrapped
