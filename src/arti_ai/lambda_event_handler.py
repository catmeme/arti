"""Lambda function to handle S3 event."""

import json

from arti_ai.app import load_data


def handler(event, _context):
    """Handle incoming events.

    Args:
        event (dict): The event data.
        _context (dict): The context data.

    Returns:
        dict: The response data.
    """
    print("Received event: " + json.dumps(event))

    load_data()

    return {"statusCode": 200, "body": json.dumps("Event processed successfully!")}
