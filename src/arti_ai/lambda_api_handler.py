"""AWS Lambda handler function for responding to arti requests."""

import base64
import json

from slack_bolt.adapter.aws_lambda import SlackRequestHandler

from .slack_app import app

SlackRequestHandler.clear_all_log_handlers()


def handler(event, context):
    """Handle the incoming event and return the response."""
    app.logger.info("Starting lambda application")
    app.logger.debug(json.dumps(event))

    if event.get("type") == "url_verification":
        decoded_body = base64.b64decode(event.get("body")).decode("utf-8")
        decoded_json = json.loads(decoded_body)
        challenge = decoded_json.get("challenge")
        app.logger.info(challenge)

        return {
            "statusCode": 200,
            "body": challenge,
        }

    slack_handler = SlackRequestHandler(app=app)
    response = slack_handler.handle(event, context)
    app.logger.debug(response)

    return response
