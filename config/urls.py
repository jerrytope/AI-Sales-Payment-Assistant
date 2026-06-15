"""
URL configuration for AI Sales Assistant.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from apps.dashboard.views import landing_view

urlpatterns = [
    # Landing Page
    path("", landing_view, name="landing"),

    # Django Admin
    path("admin/", admin.site.urls),

    # Webhooks — no auth, validated by signature
    path("webhooks/whatsapp/", include("apps.conversations.webhook_urls")),
    path("webhooks/payments/", include("apps.payments.webhook_urls")),

    # REST API
    path("api/", include("apps.customers.api_urls")),
    path("api/", include("apps.payments.api_urls")),

    # Admin Dashboard (HTML views)
    path("dashboard/", include("apps.dashboard.urls")),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
