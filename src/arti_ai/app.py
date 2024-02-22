"""The arti app."""

import os

from arti_ai.config import Config

config = Config()
os.environ["OPENAI_API_KEY"] = config.get_openai_credentials()


def ask_ai(question):
    """Ask the AI a question."""
    print(f"Processing question: {question}")

    # pylint: disable=import-outside-toplevel
    from embedchain import App  # type: ignore
    from embedchain.loaders.directory_loader import DirectoryLoader  # type: ignore

    # pylint: enable=import-outside-toplevel

    app_config = {
        "app": {
            "config": {
                "collect_metrics": False,
                "log_level": "INFO",
            }
        },
        "llm": {
            "provider": "openai",
            "config": {
                "model": "gpt-3.5-turbo-1106",
                "temperature": 0.5,
                "max_tokens": 1000,
                "top_p": 1,
            },
        },
        "embedder": {"provider": "openai"},
        "chunker": {"chunk_size": 2000, "chunk_overlap": 0, "length_function": "len"},
        "vectordb": {
            "provider": "chroma",
            "config": {"collection_name": "arti-ai", "dir": "/tmp/db", "allow_reset": True},
        },
    }

    loader = DirectoryLoader(config={"recursive": True})
    app = App.from_config(config=app_config)
    app.add("assets", loader=loader)

    return app.query(question)
