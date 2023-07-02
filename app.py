import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import chatgpt
load_dotenv()

app = App(token=os.environ.get("SLACK_BOT_TOKEN"))


@app.event("app_mention")
def respond(event, say):
    print(event['user'])
    res = chatgpt.chat("こんにちは")
    say(
        text=res
    )


@app.event("message")
def handle_message_events(body, logger):
    logger.info(body)


if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
