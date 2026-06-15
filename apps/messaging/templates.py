"""
Reusable WhatsApp message templates.
Centralized here so they can be easily edited from the dashboard in the future.
"""


def welcome_message(business_name: str) -> str:
    return (
        f"Hello! Welcome to {business_name} 👋\n\n"
        f"We're glad you reached out! How can I help you today?\n\n"
        f"You can ask about our products, pricing, or anything else."
    )


def follow_up_messages() -> list:
    return [
        "Hi! Just checking in 👋 Did you have any questions about our products? We're here to help!",
        "Hey, still thinking it over? 😊 We'd love to help you find exactly what you need!",
        "Last check-in from us! 🙏 If you'd like to learn more or are ready to order, just reply here.",
    ]


def payment_link_message(payment_url: str) -> str:
    return (
        f"Great! Here's your secure payment link 👇\n\n"
        f"💳 {payment_url}\n\n"
        f"Complete your payment and I'll send your confirmation instantly. 🎉"
    )


def payment_reminder_message(amount_naira: float, payment_url: str) -> str:
    return (
        f"Hi! Just a reminder to complete your payment of ₦{amount_naira:,.2f} 🙏\n\n"
        f"Your payment link is still active:\n{payment_url}\n\n"
        f"Need help? Just reply here!"
    )


def payment_success_message(name: str, amount_naira: float, reference: str) -> str:
    return (
        f"✅ Payment Confirmed!\n\n"
        f"Hi {name or 'there'}, we've received your payment of ₦{amount_naira:,.2f}.\n"
        f"Reference: {reference}\n\n"
        f"Thank you for your order! 🎉"
    )


def escalation_message() -> str:
    return "A human agent will be with you shortly. Thank you for your patience! 🙏"
