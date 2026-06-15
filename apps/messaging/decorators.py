import logging
import functools
from django.conf import settings
from django.http import HttpResponseForbidden
from twilio.request_validator import RequestValidator

logger = logging.getLogger(__name__)


def validate_twilio_signature(view_func):
    """
    Decorator to validate that the incoming POST request indeed originates from Twilio.
    Enabled dynamically in production settings (when settings.TWILIO_VALIDATE_SIGNATURE is True).
    """
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # 1. Check if signature validation is enabled
        validate_enabled = getattr(settings, "TWILIO_VALIDATE_SIGNATURE", not settings.DEBUG)
        if not validate_enabled:
            return view_func(request, *args, **kwargs)

        # 2. Extract Twilio signature header
        # In DRF / Django, headers can be fetched from META or headers dictionary
        signature = request.headers.get("x-twilio-signature") or request.META.get("HTTP_X_TWILIO_SIGNATURE")
        if not signature:
            logger.warning("Twilio signature validation failed: HTTP_X_TWILIO_SIGNATURE header missing")
            return HttpResponseForbidden("Forbidden: Missing signature header")

        # 3. Retrieve validation token
        auth_token = getattr(settings, "TWILIO_AUTH_TOKEN", "")
        if not auth_token:
            logger.error("Twilio validation failed: TWILIO_AUTH_TOKEN is not configured in settings")
            return HttpResponseForbidden("Forbidden: Twilio validation misconfigured")

        validator = RequestValidator(auth_token)

        # 4. Construct the absolute request URI
        url = request.build_absolute_uri()
        
        # Handle reverse proxies terminating SSL/TLS
        if request.headers.get("x-forwarded-proto") == "https" and url.startswith("http:"):
            url = url.replace("http:", "https:", 1)

        # 5. Extract the POST parameters dictionary
        # Django request.POST contains URL-encoded form data
        post_data = request.POST.dict()
        
        # Fallback to DRF request.data if request.POST is empty
        if not post_data and hasattr(request, "data"):
            if isinstance(request.data, dict):
                post_data = request.data
            elif hasattr(request.data, "dict"):
                post_data = request.data.dict()

        # 6. Execute Validation
        if not validator.validate(url, post_data, signature):
            logger.warning(f"Twilio signature validation failed for URL: {url}")
            return HttpResponseForbidden("Forbidden: Invalid signature signature verification failed")

        return view_func(request, *args, **kwargs)

    return wrapper
