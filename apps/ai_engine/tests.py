from django.test import SimpleTestCase
from unittest.mock import patch, MagicMock
from apps.ai_engine.intent_classifier import classify_intent, FALLBACK_RESPONSE


class IntentClassifierTests(SimpleTestCase):
    @patch("apps.ai_engine.intent_classifier.model")
    def test_classify_intent_success(self, mock_model):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.text = (
            '{"intent": "BUYING_INTENT", "confidence": 0.95, '
            '"reply": "Sure, the price is ₦5,000.", "product_interest": "shoe"}'
        )
        mock_model.generate_content.return_value = mock_response

        history = [{"body": "Hello", "sender_type": "USER"}]
        result = classify_intent("I want to buy a shoe", history)

        self.assertEqual(result["intent"], "BUYING_INTENT")
        self.assertEqual(result["confidence"], 0.95)
        self.assertEqual(result["reply"], "Sure, the price is ₦5,000.")
        self.assertEqual(result["product_interest"], "shoe")

    @patch("apps.ai_engine.intent_classifier.model")
    def test_classify_intent_malformed_json_fallback(self, mock_model):
        # Setup mock response with malformed JSON
        mock_response = MagicMock()
        mock_response.text = "This is not JSON"
        mock_model.generate_content.return_value = mock_response

        result = classify_intent("Hello", [])
        self.assertEqual(result, FALLBACK_RESPONSE)

    @patch("apps.ai_engine.intent_classifier.model")
    def test_classify_intent_missing_keys_fallback(self, mock_model):
        # Setup mock response with missing required keys
        mock_response = MagicMock()
        mock_response.text = '{"confidence": 0.95, "reply": "Hello"}'  # missing 'intent'
        mock_model.generate_content.return_value = mock_response

        result = classify_intent("Hello", [])
        self.assertEqual(result, FALLBACK_RESPONSE)
