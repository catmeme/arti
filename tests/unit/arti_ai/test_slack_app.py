"""Tests for the Slackbot entrypoint to arti."""

import os
import unittest
from unittest.mock import MagicMock, patch


class TestSlackbotEntrypoint(unittest.TestCase):
    """Tests for the Slackbot entrypoint to arti."""

    def setUp(self):
        """Set up tests."""
        os.environ.pop("OPENAI_API_KEY", None)

    @patch("arti_ai.slack_app.app.command")
    @patch("slack_bolt.app.app.WebClient.auth_test", return_value=MagicMock(ok=True))
    @patch("arti_ai.app.ask_ai", return_value="Response from bot.")
    def test_ack_arti_request(self, _mock_ask_ai, _mock_auth_test, _mock_app_command):
        """Test the respond_to_slack_within_3_seconds function."""
        # pylint: disable=import-outside-toplevel
        from arti_ai.slack_app import ack_arti_request

        # pylint: enable=import-outside-toplevel
        mock_ack = MagicMock()

        ack_arti_request(mock_ack)

        mock_ack.assert_called_once_with("Thinking...")

    @patch("arti_ai.slack_app.app.command")
    @patch("slack_bolt.app.app.WebClient.auth_test", return_value=MagicMock(ok=True))
    @patch("arti_ai.app.ask_ai", return_value="Response from bot.")
    def test_process_arti_request(self, _mock_ask_ai, _mock_auth_test, _mock_app_command):
        """Test the process_request function."""
        # pylint: disable=import-outside-toplevel
        from arti_ai.slack_app import handle_arti_request

        # pylint: enable=import-outside-toplevel
        mock_respond = MagicMock()
        body = {"text": "Question?"}

        with patch("arti_ai.slack_app.ask_ai", return_value="Response from bot."):
            handle_arti_request(mock_respond, body)

        mock_respond.assert_called_once_with("Q: _Question?_ A: Response from bot.")


if __name__ == "__main__":
    unittest.main()
