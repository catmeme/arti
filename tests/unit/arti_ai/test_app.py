"""Unit tests for the Arti AI app."""

import unittest
from unittest.mock import MagicMock, patch


class TestArtiApp(unittest.TestCase):
    """Test the Arti AI app."""

    @patch("builtins.print")
    @patch("embedchain.App.from_config")
    @patch("embedchain.loaders.directory_loader.DirectoryLoader")
    def test_ask_ai(self, _mock_directory_loader, mock_from_config, mock_print):
        """Test the ask_ai function."""
        # pylint: disable=import-outside-toplevel
        from arti_ai.app import ask_ai

        # pylint: enable=import-outside-toplevel

        mock_app_instance = MagicMock()
        mock_app_instance.query.return_value = "Mocked response"
        mock_from_config.return_value = mock_app_instance

        question = "What is the meaning of life?"
        expected_response = "Mocked response"

        response = ask_ai(question)

        mock_print.assert_called_with(f"Processing question: {question}")
        mock_app_instance.query.assert_called_with(question)

        self.assertEqual(response, expected_response)


if __name__ == "__main__":
    unittest.main()
