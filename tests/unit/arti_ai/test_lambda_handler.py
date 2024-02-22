"""AWS Lambda handler tests for Slack events and URL verification."""

import base64
import json
import unittest
from unittest.mock import patch


class TestLambdaHandler(unittest.TestCase):
    """AWS Lambda handler tests for Slack events and URL verification."""

    @patch("slack_bolt.adapter.aws_lambda.SlackRequestHandler")
    @patch("slack_sdk.WebClient")
    def test_general_request_handling(self, mock_web_client, mock_slack_request_handler):
        """Test handling of a general Slack event."""
        mock_web_client.return_value.auth_test.return_value = {"ok": True}

        mock_slack_request_handler_instance = mock_slack_request_handler.return_value
        mock_slack_request_handler_instance.handle.return_value = {
            "statusCode": 200,
            "body": json.dumps({"type": 4, "data": {"text": "OK"}}),
        }

        # pylint: disable=import-outside-toplevel
        from arti_ai.lambda_handler import handler

        # pylint: enable=import-outside-toplevel

        event = {"body": json.dumps({"type": "event_callback"}), "isBase64Encoded": False}

        response = handler(event, {})

        self.assertEqual(response["statusCode"], 200)
        self.assertIn("OK", json.loads(response["body"])["data"]["text"])

    @patch("arti_ai.lambda_handler.app.logger.info")
    @patch("arti_ai.lambda_handler.app.logger.debug")
    def test_url_verification(self, mock_debug, mock_info):
        """Test handling of a URL verification event."""
        # pylint: disable=import-outside-toplevel
        from arti_ai.lambda_handler import handler

        # pylint: enable=import-outside-toplevel

        challenge = "test_challenge_code"
        body_content = json.dumps({"type": "url_verification", "challenge": challenge})
        encoded_body = base64.b64encode(body_content.encode("utf-8")).decode("utf-8")

        event = {"body": encoded_body, "isBase64Encoded": True, "type": "url_verification"}

        response = handler(event, {})

        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response["body"], challenge)

        mock_info.assert_called()
        mock_debug.assert_called()


if __name__ == "__main__":
    unittest.main()
