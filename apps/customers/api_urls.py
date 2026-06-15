"""
Customer API URL routing.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CustomerViewSet, BusinessSettingViewSet, LeadCaptureView

router = DefaultRouter()
router.register(r"customers", CustomerViewSet, basename="customer")
router.register(r"settings", BusinessSettingViewSet, basename="businesssetting")

urlpatterns = [
    path("leads/", LeadCaptureView.as_view(), name="lead-capture"),
    path("", include(router.urls)),
]
