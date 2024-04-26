"""The arti app."""

import logging
import os

from arti_ai.config import Config

config_args = {}
if os.getenv("APP_CONFIG_FILE"):
    config_args["config_file"] = os.getenv("APP_CONFIG_FILE")
config = Config(**config_args)

os.environ["OPENAI_API_KEY"] = config.get_openai_credentials()
os.environ["PINECONE_API_KEY"] = config.get_pinecone_credentials()

logger = logging.getLogger(__name__)


def ask_ai(
    question: str,
    model="gpt-3.5-turbo",
    temperature=0.5,
    max_tokens=1000,
    top_p=1.0,
    prompt=None,
    system_prompt=None,
    dry_run=False,
    where=None,
    citations=False,
):  # pylint: disable=R0913
    """Query an AI model using Embedchain and return the response.

    Args:
    - query_text (str): The user's query to send to the AI.
    - model (str): Which AI model to use.
    - temperature (float): The randomness of the output.
    - max_tokens (int): The maximum number of tokens to generate.
    - top_p (float): The nucleus sampling parameter.
    - prompt (str): Custom prompt or context for the AI.
    - system_prompt (str): Custom system prompt or context for the AI.
    - dry_run (bool): Test the prompt structure without running inference.
    - where (dict): Dictionary for filtering data from the vector database.
    - citations (bool): Whether to return citations with the answer.

    Returns:
    - str | tuple: The AI's response, optionally including citations.
    """
    # pylint: disable=import-outside-toplevel
    from embedchain import App  # type: ignore
    from embedchain.config import BaseLlmConfig  # type: ignore

    # pylint: enable=import-outside-toplevel
    app = App.from_config(config=config.get_embedchain_config())

    llm_config = BaseLlmConfig(
        model=model,
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
    )

    response = app.query(input_query=question, config=llm_config, dry_run=dry_run, where=where, citations=citations)

    return response


def get_loader_and_asset_root():
    """Select and configures the appropriate loader based on AWS S3 bucket presence."""
    app_bucket_name = os.getenv("APP_BUCKET_NAME")
    root_path = os.getenv("ASSETS_ROOT_PATH", "assets")
    asset_location = root_path

    # pylint: disable=import-outside-toplevel
    if app_bucket_name:
        from arti_ai.s3_loader import S3BucketLoader  # type: ignore

        loader = S3BucketLoader()
        asset_location = f"{app_bucket_name}/{root_path}"
    else:
        from embedchain.loaders.directory_loader import DirectoryLoader  # type: ignore

        loader = DirectoryLoader(config={"recursive": True})

    # pylint: enable=import-outside-toplevel

    return loader, asset_location


def list_data_sources():
    """List data sources."""
    # pylint: disable=import-outside-toplevel
    from embedchain import App

    # pylint: enable=import-outside-toplevel

    app = App.from_config(config=config.get_embedchain_config())

    response = app.get_data_sources()

    return response


def load_data(asset_location=None):
    """Load data from data sources."""
    logger.info("Loading data")

    # pylint: disable=import-outside-toplevel
    from embedchain import App

    # pylint: enable=import-outside-toplevel

    app = App.from_config(config=config.get_embedchain_config())

    loader, primary_asset_location = get_loader_and_asset_root()
    asset_location = asset_location if asset_location is not None else primary_asset_location
    response = app.add(asset_location, loader=loader)

    return response


def reset_data():
    """Reset data in vector db."""
    logger.info("Reseting data")

    # pylint: disable=import-outside-toplevel
    from embedchain import App

    # pylint: enable=import-outside-toplevel

    app = App.from_config(config=config.get_embedchain_config())

    app.reset()
