"""Test Lambda function to handle S3 event."""

import json
import unittest
from unittest.mock import patch

from arti_ai.lambda_event_handler import handler


class TestLambdaEventHandler(unittest.TestCase):
    """AWS Lambda handler tests for events."""

    @patch("arti_ai.lambda_event_handler.load_data")
    def test_handler_calls_load_data(self, mock_load_data):
        """Test the handler calls the load_data function."""
        mock_load_data.return_value = None

        mock_event = {"key": "value"}
        mock_context = {"aws_request_id": "12345"}

        response = handler(mock_event, mock_context)

        mock_load_data.assert_called_once()

        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response["body"], json.dumps("Event processed successfully!"))


if __name__ == "__main__":
    unittest.main()
