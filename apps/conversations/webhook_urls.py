"""
WhatsApp webhook URL — receives inbound messages from Twilio.
"""

from django.urls import path
from .views import WhatsAppWebhookView

urlpatterns = [
    path("", WhatsAppWebhookView.as_view(), name="whatsapp-webhook"),
]
