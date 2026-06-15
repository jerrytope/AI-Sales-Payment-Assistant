"""
Django admin configuration for Message model.
"""

from django.contrib import admin
from .models import Message


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "customer",
        "direction",
        "sender_type",
        "detected_intent",
        "body_preview",
        "created_at",
    ]
    list_filter = ["direction", "sender_type", "detected_intent", "created_at"]
    search_fields = ["body", "customer__phone_number", "customer__name"]
    readonly_fields = ["created_at"]
    raw_id_fields = ["customer"]
    list_per_page = 50

    @admin.display(description="Message Preview")
    def body_preview(self, obj):
        return obj.body[:80] + "..." if len(obj.body) > 80 else obj.body
