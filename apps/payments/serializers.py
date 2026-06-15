"""
Order serializers for DRF API.
"""

from rest_framework import serializers
from .models import Order


class OrderSerializer(serializers.ModelSerializer):
    amount_naira = serializers.ReadOnlyField()
    customer_phone = serializers.CharField(source="customer.phone_number", read_only=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "customer",
            "customer_phone",
            "customer_name",
            "amount_kobo",
            "amount_naira",
            "currency",
            "paystack_reference",
            "payment_url",
            "status",
            "reminder_count",
            "paid_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
