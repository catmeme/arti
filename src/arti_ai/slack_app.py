"""Slackbot entrypoint to arti."""

from slack_bolt import App

from arti_ai.app import ask_ai, config

slack_bot_token, slack_bot_signing_secret = config.get_slack_credentials()
app = App(process_before_response=True, token=slack_bot_token, signing_secret=slack_bot_signing_secret)


def process_request(respond, body):
    """Process the request and respond to the user."""
    question = body["text"]
    response = ask_ai(question)
    respond(f"Q: _{question}_ A: {response}")


def respond_to_slack_within_3_seconds(ack):
    """Respond to the user within 3 seconds."""
    ack("Thinking...")


app.command("/arti")(ack=respond_to_slack_within_3_seconds, lazy=[process_request])


@app.message("knock knock")
def ask_who(_message, say):
    """Ask who's there."""
    say("_Who's there?_")
