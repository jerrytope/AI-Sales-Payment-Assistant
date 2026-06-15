"""
Paystack webhook URL — receives payment events.
"""

from django.urls import path
from .views import PaystackWebhookView

urlpatterns = [
    path("", PaystackWebhookView.as_view(), name="paystack-webhook"),
]
