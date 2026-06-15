"""
Dashboard views — serves the admin dashboard HTML pages.
Full implementation in Phase 4 (T-4.2).
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required


@login_required
def dashboard_home(request):
    """Dashboard home — redirects to conversations view."""
    return redirect("dashboard:conversations")


@login_required
def conversations_view(request):
    """Live chat view — lists customer conversations."""
    return render(request, "dashboard/conversations.html", {"active_tab": "conversations"})


@login_required
def payments_view(request):
    """Payment ledger view."""
    return render(request, "dashboard/payments.html", {"active_tab": "payments"})


@login_required
def settings_view(request):
    """Business settings editor."""
    return render(request, "dashboard/settings.html", {"active_tab": "settings"})


def landing_view(request):
    """Public landing page with lead capture form."""
    return render(request, "dashboard/landing.html")
