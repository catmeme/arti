"""Configuration settings for Arti AI."""

import json
import os

import boto3  # type: ignore
from botocore.exceptions import ClientError  # type: ignore
from dotenv import load_dotenv


class Config:
    """Configuration settings for Arti AI."""

    def __init__(self, secrets_manager_client=None):
        """Initialize the configuration settings."""
        self.secrets_manager_client = secrets_manager_client or boto3.client("secretsmanager")
        load_dotenv()

    def get_openai_credentials(self):
        """Retrieve OpenAI API key."""
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not openai_api_key:
            secret_name = self.get_env_variable("OPENAI_API_KEY_SECRET_NAME")
            secret = self.get_secret(secret_name)
            openai_api_key = secret["apiKey"]

        return openai_api_key

    def get_slack_credentials(self):
        """Retrieve Slack bot token and signing secret."""
        slack_bot_token = os.environ.get("SLACK_BOT_TOKEN")
        slack_bot_signing_secret = os.environ.get("SLACK_BOT_TOKEN_SECRET_NAME")
        if not slack_bot_token:
            slack_bot_secret = self.get_secret(secret_name=self.get_env_variable("SLACK_BOT_TOKEN_SECRET_NAME"))
            slack_bot_token = slack_bot_secret["apiKey"]
            slack_bot_signing_secret = slack_bot_secret["signingSecret"]

        return (slack_bot_token, slack_bot_signing_secret)

    @staticmethod
    def get_env_variable(name):
        """Get the environment variable or raise exception.

        Args:
            name (str): The name of the environment variable.
        """
        try:
            return os.environ[name]
        except KeyError as e:
            raise EnvironmentError(f"Failed to find {name} in environment variables.") from e

    def get_secret(self, secret_name):
        """Retrieve secret from AWS Secrets Manager.

        Args:
            secret_name (str): The name of the secret to retrieve.
        """
        try:
            response = self.secrets_manager_client.get_secret_value(SecretId=secret_name)
            return json.loads(response["SecretString"])
        except ClientError as e:
            print(f"Error retrieving secret {secret_name}: {e}")
            return None
