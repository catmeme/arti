"""Tests for the Slackbot entrypoint to arti."""

import unittest
from unittest.mock import patch, MagicMock


class TestSlackbotEntrypoint(unittest.TestCase):
    """Tests for the Slackbot entrypoint to arti."""

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


if __name__ == "__main__":
    unittest.main()
