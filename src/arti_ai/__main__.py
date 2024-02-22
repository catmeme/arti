"""CLI entrypoint to arti."""

import argparse

from arti_ai.app import ask_ai


def handle_ask(question):
    """Handle the ask command."""
    print(ask_ai(" ".join(question)))


def main():
    """Entrypoint to CLI."""
    parser = argparse.ArgumentParser(description="CLI entrypoint to ask questions to the AI model.")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    parser_ask = subparsers.add_parser("ask", help="Ask a question")
    parser_ask.add_argument("question", nargs="+", type=str, help="The question you want to ask")

    args = parser.parse_args()

    if args.command == "ask":
        handle_ask(args.question)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
