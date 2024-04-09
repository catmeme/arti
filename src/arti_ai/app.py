"""The arti app."""

import os

from arti_ai.config import Config

config_args = {}
if os.getenv("APP_CONFIG_FILE"):
    config_args["config_file"] = os.getenv("APP_CONFIG_FILE")
config = Config(**config_args)

os.environ["OPENAI_API_KEY"] = config.get_openai_credentials()
os.environ["PINECONE_API_KEY"] = config.get_pinecone_credentials()


def ask_ai(question: str):
    """Ask the AI a question."""
    print(f"Processing question: {question}")

    # pylint: disable=import-outside-toplevel
    from embedchain import App  # type: ignore

    # pylint: enable=import-outside-toplevel

    app = App.from_config(config=config.get_embedchain_config())

    return app.query(question)


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


def load_data():
    """Load data from data sources."""
    print("Loading data")

    # pylint: disable=import-outside-toplevel
    from embedchain import App

    # pylint: enable=import-outside-toplevel

    app = App.from_config(config=config.get_embedchain_config())

    loader, asset_location = get_loader_and_asset_root()
    response = app.add(asset_location, loader=loader)

    return response


def reset_data():
    """Reset data in vector db."""
    print("Reseting data")

    # pylint: disable=import-outside-toplevel
    from embedchain import App

    # pylint: enable=import-outside-toplevel

    app = App.from_config(config=config.get_embedchain_config())

    app.reset()
