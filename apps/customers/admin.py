"""
Django admin configuration for Customer and BusinessSetting models.
"""

from django.contrib import admin
from .models import Customer, BusinessSetting


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "phone_number",
        "name",
        "workflow_state",
        "human_takeover",
        "follow_up_count",
        "source",
        "last_message_at",
        "created_at",
    ]
    list_filter = ["workflow_state", "human_takeover", "source", "created_at"]
    search_fields = ["phone_number", "name", "email"]
    readonly_fields = ["created_at", "updated_at"]
    list_per_page = 25

    fieldsets = (
        ("Contact Info", {
            "fields": ("phone_number", "name", "email"),
        }),
        ("Workflow", {
            "fields": ("workflow_state", "follow_up_count", "last_message_at"),
        }),
        ("Human Takeover", {
            "fields": ("human_takeover", "takeover_by"),
        }),
        ("Metadata", {
            "fields": ("source", "extra_data", "created_at", "updated_at"),
        }),
    )


@admin.register(BusinessSetting)
class BusinessSettingAdmin(admin.ModelAdmin):
    list_display = ["setting_key", "setting_value_preview", "description", "updated_at"]
    search_fields = ["setting_key", "description"]
    readonly_fields = ["updated_at"]

    @admin.display(description="Value Preview")
    def setting_value_preview(self, obj):
        """Show a truncated preview of the setting value."""
        value = obj.setting_value
        return value[:80] + "..." if len(value) > 80 else value
