"""Tests for the CLI entrypoint of the Arti AI package."""

import argparse
import io
import sys
import unittest
from unittest.mock import patch

from arti_ai.__main__ import handle_ask, main


class TestCLIEntrypoint(unittest.TestCase):
    """Test the CLI entrypoint."""

    def setUp(self):
        """Set up the test."""
        self.parser_output = io.StringIO()
        sys.stdout = self.parser_output

    def tearDown(self):
        """Tear down the test."""
        sys.stdout = sys.__stdout__

    @patch("arti_ai.__main__.ask_ai")
    def test_handle_ask(self, mock_ask_ai):
        """Test the handle_ask function."""
        test_question = "What is the meaning of life?"
        expected_answer = "42"
        mock_ask_ai.return_value = expected_answer

        handle_ask([test_question])

        self.assertIn(expected_answer, self.parser_output.getvalue())

    @patch("argparse.ArgumentParser.parse_args")
    @patch("arti_ai.__main__.handle_ask")
    def test_main_ask_command(self, mock_handle_ask, mock_parse_args):
        """Test the main function with the ask command."""
        test_question = ["What is the meaning of life?"]
        mock_parse_args.return_value = argparse.Namespace(command="ask", question=test_question)

        main()

        mock_handle_ask.assert_called_once_with(test_question)

    @patch("arti_ai.__main__.load_data")
    @patch("argparse.ArgumentParser.parse_args")
    def test_main_load_command(self, mock_parse_args, mock_load_data):
        """Test the main function with the 'load' command."""
        mock_parse_args.return_value = argparse.Namespace(command="load")
        mock_load_data.return_value = None  # Adjust based on the actual behavior of load_data

        main()

        mock_load_data.assert_called_once()

    @patch("arti_ai.__main__.reset_data")
    @patch("argparse.ArgumentParser.parse_args")
    def test_main_reset_command(self, mock_parse_args, mock_reset_data):
        """Test the main function with the 'reset' command."""
        mock_parse_args.return_value = argparse.Namespace(command="reset")
        mock_reset_data.return_value = None  # Adjust based on the actual behavior of reset_data

        main()

        mock_reset_data.assert_called_once()

    @patch("argparse.ArgumentParser.parse_args")
    def test_main_not_command(self, mock_parse_args):
        """Test the main function with a command other than ask."""
        mock_parse_args.return_value = argparse.Namespace(command="not-a-command")

        main()


if __name__ == "__main__":
    unittest.main()
