"""This module contains the Lambda function handler for processing S3 events from SQS messages."""

import json
import logging
import os

from arti_ai.app import load_data

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def handler(event, context):  # pylint: disable=unused-argument
    """Handle incoming S3 events from SQS messages.

    Args:
        event (dict): The event data.
        context (dict): The context data.

    Returns:
        dict: The response data.
    """
    logger.info("Starting lambda application")
    logger.debug(event)

    app_bucket_name = os.environ["APP_BUCKET_NAME"]

    for record in event.get("Records", []):
        try:
            s3_event = json.loads(record.get("body", "{}"))
        except json.JSONDecodeError:
            logger.info("Failed to decode S3 event from SQS message body.")
            continue

        for s3_record in s3_event.get("Records", []):
            object_key = s3_record.get("s3", {}).get("object", {}).get("key")
            if object_key:
                logger.info("Processed %s in bucket %s.", object_key, app_bucket_name)
                load_data(asset_location=f"{app_bucket_name}/{object_key}")
            else:
                logger.info("Object key not found in S3 event.")

    return {"statusCode": 200, "body": json.dumps("Successfully processed S3 event(s) from SQS messages.")}
