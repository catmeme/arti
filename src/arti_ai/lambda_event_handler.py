"""Lambda function to handle S3 event."""

import json
import logging

from arti_ai.app import load_data

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def handler(event, _context):
    """Handle incoming events.

    Args:
        event (dict): The event data.
        _context (dict): The context data.

    Returns:
        dict: The response data.
    """
    logger.info("Starting lambda application")
    logger.debug(event)

    load_data()

    return {"statusCode": 200, "body": json.dumps("Event processed successfully!")}
