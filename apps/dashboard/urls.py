"""
Dashboard URL routing.
"""

from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.dashboard_home, name="home"),
    path("conversations/", views.conversations_view, name="conversations"),
    path("payments/", views.payments_view, name="payments"),
    path("settings/", views.settings_view, name="settings"),
]
