"""
Django admin configuration for Order model.
"""

from django.contrib import admin
from .models import Order


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "customer",
        "amount_display",
        "currency",
        "status",
        "paystack_reference",
        "reminder_count",
        "paid_at",
        "created_at",
    ]
    list_filter = ["status", "currency", "created_at"]
    search_fields = [
        "paystack_reference",
        "customer__phone_number",
        "customer__name",
    ]
    readonly_fields = ["created_at", "updated_at", "gateway_response"]
    raw_id_fields = ["customer"]
    list_per_page = 25

    @admin.display(description="Amount (₦)")
    def amount_display(self, obj):
        return f"₦{obj.amount_naira:,.2f}"
