"""
Google Gemini API client wrapper.
Full implementation in Phase 2 (T-2.3).
"""

import logging
import google.generativeai as genai
from django.conf import settings

logger = logging.getLogger(__name__)

# Configure Gemini on module load
genai.configure(api_key=settings.GEMINI_API_KEY)

# Use gemini-1.5-flash for speed and cost-efficiency
model = genai.GenerativeModel("gemini-1.5-flash")
