"""Configuration settings for Arti AI."""

import json
import os
from pathlib import Path

import boto3  # type: ignore
import yaml
from botocore.exceptions import ClientError  # type: ignore
from dotenv import load_dotenv


class Config:
    """Configuration settings for Arti AI."""

    def __init__(self, config_file="config/config.yaml", secrets_manager_client=None):
        """Initialize the configuration settings."""
        self.secrets_manager_client = secrets_manager_client or boto3.client("secretsmanager")
        self.project_root = Path(__file__).resolve().parents[2]
        self.config_file = self.project_root / config_file
        load_dotenv()

    def get_embedchain_config(self):
        """Load and return the EmbedChain app configuration from a YAML file.

        Raises:
            FileNotFoundError: If the YAML file cannot be found.
            yaml.YAMLError: If there is an error parsing the YAML file.
        """
        try:
            with open(self.config_file, "r", encoding="utf-8") as file:
                return yaml.safe_load(file)
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Configuration file not found: {self.config_file}") from e
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Error parsing YAML configuration: {self.config_file}") from e

    def get_openai_credentials(self):
        """Retrieve OpenAI API key."""
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not openai_api_key:
            secret_name = self.get_env_variable("OPENAI_API_KEY_SECRET_NAME")
            secret = self.get_secret(secret_name)
            openai_api_key = secret["apiKey"]

        return openai_api_key

    def get_pinecone_credentials(self):
        """Retrieve OpenAI API key."""
        pinecone_api_key = os.environ.get("PINECONE_API_KEY")
        if not pinecone_api_key:
            secret_name = self.get_env_variable("PINECONE_API_KEY_SECRET_NAME")
            secret = self.get_secret(secret_name)
            pinecone_api_key = secret["apiKey"]

        return pinecone_api_key

    def get_slack_credentials(self):
        """Retrieve Slack bot token and signing secret."""
        slack_bot_token = os.environ.get("SLACK_BOT_TOKEN")
        slack_bot_signing_secret = os.environ.get("SLACK_BOT_TOKEN_SECRET_NAME")
        if not slack_bot_token:
            slack_bot_secret = self.get_secret(secret_name=self.get_env_variable("SLACK_BOT_TOKEN_SECRET_NAME"))
            slack_bot_token = slack_bot_secret["apiKey"]
            slack_bot_signing_secret = slack_bot_secret["signingSecret"]

        return slack_bot_token, slack_bot_signing_secret

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
