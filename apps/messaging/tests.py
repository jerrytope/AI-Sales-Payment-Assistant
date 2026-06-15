from django.test import SimpleTestCase
from unittest.mock import patch, MagicMock
from apps.messaging.twilio_client import TwilioWhatsAppClient


class TwilioWhatsAppClientTests(SimpleTestCase):
    @patch("apps.messaging.twilio_client.Client")
    def test_send_message_success(self, mock_client_class):
        # Setup mock client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_message = MagicMock()
        mock_message.sid = "SM12345"
        mock_client.messages.create.return_value = mock_message

        # Instantiate twilio client
        with self.settings(
            TWILIO_ACCOUNT_SID="ACtest",
            TWILIO_AUTH_TOKEN="test_token",
            TWILIO_WHATSAPP_NUMBER="+14155238886",
        ):
            client = TwilioWhatsAppClient()
            sid = client.send_message("+2348012345678", "Hello World")

            # Assertions
            self.assertEqual(sid, "SM12345")
            mock_client.messages.create.assert_called_once_with(
                from_="whatsapp:+14155238886",
                to="whatsapp:+2348012345678",
                body="Hello World",
            )

    @patch("apps.messaging.twilio_client.Client")
    def test_send_message_with_media(self, mock_client_class):
        # Setup mock client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_message = MagicMock()
        mock_message.sid = "SM12345"
        mock_client.messages.create.return_value = mock_message

        # Instantiate twilio client
        with self.settings(
            TWILIO_ACCOUNT_SID="ACtest",
            TWILIO_AUTH_TOKEN="test_token",
            TWILIO_WHATSAPP_NUMBER="+14155238886",
        ):
            client = TwilioWhatsAppClient()
            sid = client.send_message(
                "+2348012345678", "Hello World", media_url="http://example.com/image.png"
            )

            # Assertions
            self.assertEqual(sid, "SM12345")
            mock_client.messages.create.assert_called_once_with(
                from_="whatsapp:+14155238886",
                to="whatsapp:+2348012345678",
                body="Hello World",
                media_url=["http://example.com/image.png"],
            )
