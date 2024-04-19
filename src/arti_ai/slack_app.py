"""Slackbot entrypoint to arti."""

import json
import os
from pathlib import Path

import boto3
import requests
from slack_bolt import App

from arti_ai.app import ask_ai, config, list_data_sources

slack_bot_token, slack_bot_signing_secret = config.get_slack_credentials()
app = App(process_before_response=True, token=slack_bot_token, signing_secret=slack_bot_signing_secret)
s3_client = boto3.client("s3", region_name=os.environ["AWS_REGION"])


def format_as_block_kit(summary, details):
    """
    Format the response using Slack Block Kit with enhanced layout and truncation for long texts.

    Args:
        summary (str): The main text or summary of the response.
        details (list of tuple): List containing details and metadata about the sources.

    Returns:
        dict: A structured message in the format of Slack Block Kit.
    """
    # Initial block with the summary
    blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": summary}}, {"type": "divider"}]

    # Append details to the blocks
    for detail, metadata in details:
        # Truncate detail text to 300 characters for display
        truncated_text = (detail[:300] + "...") if len(detail) > 300 else detail
        source_url = metadata.get("url", "No URL provided")
        source_score = metadata.get("score", "No score provided")
        text_detail = f"*Score*: {source_score}\n*Source*: <{source_url}|{source_url}>\n*Detail*: {truncated_text}"

        detail_block = {"type": "section", "text": {"type": "mrkdwn", "text": text_detail}}
        blocks.append(detail_block)

    message = {"blocks": blocks}
    return message


def get_bot_user_id():
    """Get the bot user id."""
    response = requests.post(
        "https://slack.com/api/auth.test", headers={"Authorization": f"Bearer {slack_bot_token}"}, timeout=30
    )
    if response.status_code == 200 and response.json()["ok"]:
        return response.json()["user_id"]
    return None


def ack_arti_request(ack):
    """Ack arti request."""
    ack("Thinking...")


def ack_file_shared(ack):
    """Ack app_mention."""
    ack()


def ack_app_mention(ack):
    """Ack app_mention."""
    ack("Thinking...")


def ack_app_home_opened(ack):
    """Ack app_home_opened."""
    ack()


def ack_smarti_request(ack):
    """Ack smarti request."""
    ack()


def handle_app_mention(event, say, client):
    """Handle bot mentions."""
    text = event["text"]
    bot_user_id = client.auth_test()["user_id"]

    # Strip the mention of the bot to isolate the command and arguments
    command_text = text.split(f"<@{bot_user_id}>")[1].strip() if f"<@{bot_user_id}>" in text else text

    # Parse the command and arguments
    parts = command_text.split(maxsplit=1)
    if not parts:
        say("I need a command to do something useful!")
        return

    # Get the command and the remainder of the message as arguments
    command = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    if command == "ask":
        if args:
            response = ask_ai(question=args)
            say(response)
        else:
            say("Please provide a question to ask.")
    elif command == "list":
        say(json.dumps(list_data_sources()))
    else:
        say(f"Sorry, I don't recognize the command `{command}`.")


def handle_arti_request(respond, body):
    """Process the request and respond to the user."""
    question = body["text"]
    response = ask_ai(question=question)
    respond(f"Q: _{question}_ A: {response}")


def handle_app_home_opened(client, event, logger):
    """Display a home tab."""
    try:
        diagram_image_url = (
            "https://github.com/catmeme/arti/blob/main/docs/images/arti-architecture-blog-2.png?raw=true"
        )

        blocks = [
            {"type": "section", "text": {"type": "mrkdwn", "text": "Welcome to your Home tab!"}},
            {
                "type": "image",
                "title": {"type": "plain_text", "text": "How Arti Works"},
                "image_url": diagram_image_url,
                "alt_text": "Arti Workflow Diagram",
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "To see a list of items in our S3 bucket, click the button below!"},
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "List S3 Objects"},
                        "action_id": "list_s3_objects",
                    }
                ],
            },
        ]

        client.views_publish(user_id=event["user"], view={"type": "home", "blocks": blocks})
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"Failed to publish Home tab: {e}")


def handle_file_uploads(event, say, client, logger):
    """Handle file uploads by bridging to S3."""
    file_id = event["file"]["id"]
    channel_id = event["channel_id"]

    try:  # pylint: disable=too-many-nested-blocks
        file_info = client.files_info(token=slack_bot_token, file=file_id)["file"]
        file_url = file_info["url_private_download"]

        headers = {"Authorization": f"Bearer {slack_bot_token}"}
        response = requests.get(file_url, headers=headers, stream=True, timeout=30)

        if response.status_code == 200:
            s3_client.upload_fileobj(Fileobj=response.raw, Bucket=os.getenv("APP_BUCKET_NAME"), Key=file_info["name"])

            # Fetch recent messages to find the correct timestamp
            messages = client.conversations_history(channel=channel_id, limit=10)["messages"]
            for msg in messages:
                if msg.get("files") and any(f["id"] == file_id for f in msg.get("files", [])):
                    # Found the message with the correct file
                    message_ts = msg["ts"]
                    client.reactions_add(channel=channel_id, name="white_check_mark", timestamp=message_ts)
                    # Respond in a thread to the message containing the file
                    say(
                        text=f"File `{file_info['name']}` uploaded to S3! :tada:",  # pylint: disable=W1405
                        thread_ts=message_ts,
                    )
                    return

            logger.error("No valid message found for reaction.")

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"Error processing file: {str(e)}")
        # Use the initially captured message_ts if available for error handling in thread
        if "message_ts" in locals():
            say(text=f"Failed to upload file to S3: {str(e)} :x:", thread_ts=message_ts)
        else:
            say(text=f"Failed to upload file to S3: {str(e)} :x:")


@app.action("list_s3_objects")
def handle_list_s3_objects(ack, body, client, logger):
    """Handle button click to list S3 objects."""
    ack()
    try:
        response = s3_client.list_objects_v2(Bucket=os.getenv("APP_BUCKET_NAME"))
        objects = response.get("Contents", [])
        if not objects:
            message_text = "No objects found in the S3 bucket."
        else:
            message_text = "Objects in S3 bucket:\n" + "\n".join(obj["Key"] for obj in objects)

        # Update the message to show the objects or a not-found message
        client.chat_postMessage(channel=body["user"]["id"], text=message_text)
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"Error listing S3 objects: {e}")
        client.chat_postMessage(channel=body["user"]["id"], text="Failed to list objects in S3.")


@app.event("message")
def handle_message_events(message, say):
    """Handle message events."""
    if message.get("subtype") is None:  # This checks that it's a user-sent message, not a bot message or other subtype
        text = message.get("text", "")
        if "hello" in text.lower():
            say("Hello back to you!")


@app.event("reaction_added")
def handle_reaction_added(event, say, logger):
    """Handle reaction event."""
    reaction = event["reaction"]
    user_id = event["user"]
    item_user = event.get("item_user")
    logger.info(f"Reaction: {reaction} added by {user_id}")

    bot_user_id = get_bot_user_id()

    if item_user == bot_user_id:
        say(text=f"Thanks for reacting with :{reaction}: on my message!")


@app.command("/smarti")
def open_smarti_modal(ack, body, client):
    """Open smarti model."""
    ack()
    modal_file_path = Path(config.project_root) / "config" / "slack_modals" / "chat.json"
    print(body)
    channel_id = body["channel_id"]  # Capture the channel ID from the command body

    with open(modal_file_path, "r", encoding="utf-8") as json_file:
        modal_view = json.load(json_file)

    modal_view["blocks"].insert(
        0, {"type": "section", "text": {"type": "mrkdwn", "text": f"*Channel:* <#{channel_id}>"}}
    )

    modal_view["private_metadata"] = channel_id

    client.views_open(trigger_id=body["trigger_id"], view=modal_view)


def handle_smarti_submission(client, logger, body, view):  # pylint: disable=R0914
    """Handle smarti submission."""
    logger.info("Handling smarti submission")
    print(body)
    try:
        values = view["state"]["values"]
        question = values["question"]["input"]["value"]
        model = values["model"]["input"]["selected_option"]["value"]
        temperature = float(values["temperature"]["input"]["value"])
        max_tokens = int(values["max_tokens"]["input"]["value"])
        top_p = float(values["top_p"]["input"]["value"])
        prompt = values["prompt"]["input"]["value"]
        system_prompt = values["system_prompt"]["input"]["value"]
        citation_options = values["citations"]["input"].get("selected_options", [])
        citations = any(option["value"] == "true" for option in citation_options)

        ai_response = ask_ai(
            question=question,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            prompt=prompt,
            system_prompt=system_prompt,
            citations=citations,
        )

        channel_id = view["private_metadata"]
        if not channel_id:
            channel_id = body["user"]["id"]

        if isinstance(ai_response, tuple) and len(ai_response) == 2:
            summary, details = ai_response
            initial_response = format_as_block_kit(summary, [])  # Send only summary initially
        else:
            initial_response = {"text": ai_response}

        # Post the initial summary to the channel or user DM
        result = client.chat_postMessage(
            channel=channel_id, blocks=initial_response.get("blocks"), text=initial_response.get("text")
        )
        thread_ts = result["ts"]  # Timestamp of the message to start threading

        if isinstance(ai_response, tuple) and details:
            # If details are available, post them in a thread
            detailed_response = format_as_block_kit("Detailed Information:", details)
            client.chat_postMessage(channel=channel_id, thread_ts=thread_ts, blocks=detailed_response.get("blocks"))

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"Error handling modal submission: {e}")
        user_id = body.get("user", {}).get("id", "default_user_id")
        client.chat_postMessage(channel=user_id, text="Failed to process your request. Please try again.")


app.command("/arti")(ack=ack_arti_request, lazy=[handle_arti_request])
app.event("app_home_opened")(ack=ack_app_home_opened, lazy=[handle_app_home_opened])
app.event("app_mention")(ack=ack_app_mention, lazy=[handle_app_mention])
app.event("file_shared")(ack=ack_file_shared, lazy=[handle_file_uploads])
app.view("smarti_modal")(ack=ack_smarti_request, lazy=[handle_smarti_submission])
