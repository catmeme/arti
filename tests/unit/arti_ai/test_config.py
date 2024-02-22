"""Unit tests for the Config class."""

import json
import os
import unittest
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError  # type: ignore

from arti_ai.config import Config


class TestConfig(unittest.TestCase):
    """Test the Config class."""

    def setUp(self):
        """Set up the test."""
        self.config = Config(secrets_manager_client=MagicMock())

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test_api_key"}, clear=True)
    def test_get_openai_credentials_from_env(self):
        """Test getting OpenAI credentials from environment variable."""
        openai_api_key = self.config.get_openai_credentials()
        self.assertEqual(openai_api_key, "test_api_key")

    @patch.dict(os.environ, {}, clear=True)
    @patch("arti_ai.config.Config.get_env_variable", return_value="fake_secret_name")
    @patch("arti_ai.config.Config.get_secret", return_value={"apiKey": "fetched_api_key"})
    def test_get_openai_credentials_from_secret(self, mock_get_secret, _mock_get_env_variable):
        """Test getting OpenAI credentials from secret."""
        openai_api_key = self.config.get_openai_credentials()
        self.assertEqual(openai_api_key, "fetched_api_key")
        mock_get_secret.assert_called_with("fake_secret_name")

    @patch.dict(os.environ, {}, clear=True)
    @patch("arti_ai.config.Config.get_env_variable", side_effect=["fake_slack_token_secret_name"])
    @patch(
        "arti_ai.config.Config.get_secret",
        return_value={"apiKey": "fetched_slack_token", "signingSecret": "fetched_signing_secret"},
    )
    def test_get_slack_credentials_from_secret(self, _mock_get_secret, _mock_get_env_variable):
        """Test getting Slack credentials from secret."""
        slack_bot_token, slack_bot_signing_secret = self.config.get_slack_credentials()
        self.assertEqual(slack_bot_token, "fetched_slack_token")
        self.assertEqual(slack_bot_signing_secret, "fetched_signing_secret")

    def test_get_env_variable_found(self):
        """Test getting an environment variable that exists."""
        with patch.dict(os.environ, {"SOME_VAR": "some_value"}, clear=True):
            self.assertEqual(Config.get_env_variable("SOME_VAR"), "some_value")

    def test_get_env_variable_not_found(self):
        """Test getting an environment variable that does not exist."""
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(EnvironmentError):
            Config.get_env_variable("MISSING_VAR")

    @patch("arti_ai.config.boto3.client")
    def test_get_secret(self, mock_boto_client):
        """Test getting a secret from AWS Secrets Manager."""
        secret_value = {"apiKey": "test_api_key"}
        secret_string = json.dumps(secret_value)
        mock_client_instance = MagicMock()
        mock_client_instance.get_secret_value.return_value = {"SecretString": secret_string}
        mock_boto_client.return_value = mock_client_instance

        config = Config()
        result = config.get_secret("OPENAI_API_KEY_SECRET_NAME")

        self.assertEqual(result["apiKey"], "test_api_key")
        mock_boto_client.assert_called_once_with("secretsmanager")

    @patch("arti_ai.config.boto3.client")
    def test_get_secret_client_error(self, mock_boto_client):
        """Test getting a secret that does not exist."""
        mock_client_instance = MagicMock()
        mock_client_instance.get_secret_value.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException", "Message": "Secret not found"}}, "get_secret_value"
        )
        mock_boto_client.return_value = mock_client_instance

        config = Config()
        result = config.get_secret("nonexistent_secret")

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
