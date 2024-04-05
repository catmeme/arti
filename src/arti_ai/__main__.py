"""CLI entrypoint to arti."""

import argparse

from arti_ai.app import ask_ai, load_data, reset_data


def handle_ask(question):
    """Handle the ask command."""
    print(ask_ai(question))


def main():
    """Entrypoint to CLI."""
    parser = argparse.ArgumentParser(description="CLI entrypoint to ask questions to the AI model.")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    parser_ask = subparsers.add_parser("ask", help="Ask a question")
    parser_ask.add_argument("question", type=str, help="The question you want to ask")

    subparsers.add_parser("load", help="Load data from data sources")

    subparsers.add_parser("reset", help="Reset data in vector database")

    args = parser.parse_args()

    if args.command == "ask":
        handle_ask(args.question)
    elif args.command == "load":
        load_data()
    elif args.command == "reset":
        reset_data()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
