"""AWS Lambda handler function for responding to arti requests."""

import base64
import json
import logging

from slack_bolt.adapter.aws_lambda import SlackRequestHandler

from .slack_app import app

SlackRequestHandler.clear_all_log_handlers()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def handler(event, context):
    """Handle the incoming event and return the response."""
    logger.info("Starting lambda application")
    logger.debug(event)

    if event.get("type") == "url_verification":
        decoded_body = base64.b64decode(event.get("body")).decode("utf-8")
        decoded_json = json.loads(decoded_body)
        challenge = decoded_json.get("challenge")
        logger.debug(challenge)

        return {
            "statusCode": 200,
            "body": challenge,
        }

    slack_handler = SlackRequestHandler(app=app)
    response = slack_handler.handle(event, context)
    logger.info(response)

    return response
