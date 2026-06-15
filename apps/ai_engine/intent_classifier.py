"""
Intent classifier — uses Google Gemini to classify customer messages.
Full implementation in Phase 2 (T-2.3).
"""

import json
import logging
from .gemini_client import model

logger = logging.getLogger(__name__)

INTENT_SYSTEM_PROMPT = """
You are an AI sales assistant for a Nigerian business.
Analyze the customer's latest message in context of the conversation history.
Return a JSON object with exactly these keys:
  - intent: one of [GREETING, PRODUCT_INQUIRY, BUYING_INTENT, OBJECTION, SUPPORT_OR_HUMAN, UNKNOWN]
  - confidence: float 0.0 to 1.0
  - reply: a short, friendly, Nigerian-market-appropriate response in plain text (no markdown)
  - product_interest: name of product mentioned, or null
"""

FALLBACK_RESPONSE = {
    "intent": "UNKNOWN",
    "confidence": 0.0,
    "reply": "I'm here to help! What would you like to know?",
    "product_interest": None,
}


def classify_intent(message: str, history: list) -> dict:
    """
    Classify the intent of a customer message using Gemini.

    Args:
        message: The customer's latest message
        history: List of recent messages [{body, sender_type}, ...]

    Returns:
        dict with intent, confidence, reply, product_interest
    """
    history_text = "\n".join(
        [
            f"{'Customer' if m['sender_type'] == 'USER' else 'Assistant'}: {m['body']}"
            for m in reversed(history)
        ]
    )
    prompt = (
        f"{INTENT_SYSTEM_PROMPT}\n\n"
        f"Conversation History:\n{history_text}\n\n"
        f"Latest message: {message}\n\n"
        f"Respond ONLY with valid JSON."
    )

    try:
        response = model.generate_content(prompt)
        raw = response.text.strip().lstrip("```json").rstrip("```").strip()
        parsed = json.loads(raw)

        # Validate required keys
        required = {"intent", "confidence", "reply"}
        if not required.issubset(parsed.keys()):
            logger.warning(f"Gemini response missing keys: {parsed}")
            return FALLBACK_RESPONSE

        return parsed

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Gemini JSON response: {e}")
        return FALLBACK_RESPONSE
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return FALLBACK_RESPONSE
