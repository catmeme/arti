"""Tests for the Slackbot entrypoint to arti."""

import os
import unittest
from unittest.mock import MagicMock, patch


class TestSlackbotEntrypoint(unittest.TestCase):
    """Tests for the Slackbot entrypoint to arti."""

    def setUp(self):
        """Set up tests."""
        os.environ.pop("OPENAI_API_KEY", None)

    @patch("arti_ai.slack_app.app.message")
    @patch("slack_bolt.app.app.WebClient.auth_test", return_value=MagicMock(ok=True))
    @patch("openai.Completion.create", return_value=MagicMock(choices=[MagicMock(text="Who's there?")]))
    @patch("arti_ai.app.ask_ai", return_value="Just a simple bot.")
    def test_ask_who(self, _mock_ask_ai, _mock_openai, _mock_auth_test, _mock_app_message):
        """Test the ask_who function."""
        # pylint: disable=import-outside-toplevel
        from arti_ai.slack_app import ask_who

        # pylint: enable=import-outside-toplevel

        mock_say = MagicMock()
        message = {"text": "knock knock", "channel": "C1234567890"}

        ask_who(message, mock_say)  # type: ignore

    @patch("arti_ai.slack_app.app.command")
    @patch("slack_bolt.app.app.WebClient.auth_test", return_value=MagicMock(ok=True))
    @patch("arti_ai.app.ask_ai", return_value="Response from bot.")
    def test_process_request(self, _mock_ask_ai, _mock_auth_test, _mock_app_command):
        """Test the process_request function."""
        # pylint: disable=import-outside-toplevel
        from arti_ai.slack_app import process_request

        # pylint: enable=import-outside-toplevel
        mock_respond = MagicMock()
        body = {"text": "Question?"}

        with patch("arti_ai.slack_app.ask_ai", return_value="Response from bot."):
            process_request(mock_respond, body)

        mock_respond.assert_called_once_with("Q: _Question?_ A: Response from bot.")

    @patch("arti_ai.slack_app.app.command")
    @patch("slack_bolt.app.app.WebClient.auth_test", return_value=MagicMock(ok=True))
    @patch("arti_ai.app.ask_ai", return_value="Response from bot.")
    def test_respond_to_slack_within_3_seconds(self, _mock_ask_ai, _mock_auth_test, _mock_app_command):
        """Test the respond_to_slack_within_3_seconds function."""
        # pylint: disable=import-outside-toplevel
        from arti_ai.slack_app import respond_to_slack_within_3_seconds

        # pylint: enable=import-outside-toplevel
        mock_ack = MagicMock()

        respond_to_slack_within_3_seconds(mock_ack)

        mock_ack.assert_called_once_with("Thinking...")


if __name__ == "__main__":
    unittest.main()
