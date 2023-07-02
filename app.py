import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import chatgpt
import re
import datetime

from sqlalchemy.orm import sessionmaker
from database import engine
from models import Bot, Template

load_dotenv()

app = App(token=os.environ.get("SLACK_BOT_TOKEN"))
Session = sessionmaker(bind=engine)


@app.event("app_mention")
def respond(event, say):
    print("event", event)
    print(event['user'])
    print(event['text'].split())
    print(event['channel'])
    try:
        user = event['user']
        text = event["text"]
        channel = event["channel"]
        text = create_bot_filter(text, user, channel)
        text = set_template_to_bot_filter(text, user, channel)
        text = create_template_filter(text, user, channel)
        text = delete_template_filter(text, user, channel)
        text = set_template_filter(text, user, channel)
        text = show_templates_filter(text, user, channel)
        text = show_bots_filter(text, user, channel)
    except Exception as e:
        text = str(e)
    say(
        text=text
    )


def delete_template_filter(text, user, channel):
    pattern = r'\A<[^>]*> delete template (\S+)'
    result = re.match(pattern, text)
    if not result:
        return text
    template_name = result.group(1)
    session = Session()
    template = session.query(Template).filter(
        Template.name == template_name).first()
    if not template:
        raise Exception(f"error: template {template_name} not found")
    if template.owner_slack_id != user:
        raise Exception("error: permission error")
    session.delete(template)
    session.commit()
    return f"template {template_name} deleted"


def delete_bot_filter(text, user, channel):
    pattern = r'\A<[^>]*> delete bot (\S+)'
    result = re.match(pattern, text)
    if not result:
        return text
    bot_name = result.group(1)
    session = Session()
    bot = session.query(Bot).filter(
        Bot.name == bot_name).first()
    if not bot:
        raise Exception(f"error: bot {bot_name} not found")
    if bot.owner_slack_id != user:
        raise Exception("error: permission error")
    session.delete(bot)
    session.commit()
    return f"bot {bot_name} deleted"


def show_templates_filter(text, user, channel):
    pattern = r'\A<[^>]*> show templates'
    result = re.match(pattern, text)
    if not result:
        return text
    session = Session()
    templates = session.query(Template).order_by(Template.id)
    template_names = [template.name for template in templates]
    return "\n".join(template_names)


def show_bots_filter(text, user, channel):
    pattern = r'\A<[^>]*> show bots'
    result = re.match(pattern, text)
    if not result:
        return text
    session = Session()
    bots = session.query(Bot).order_by(Bot.id)
    bot_names = [bot.name for bot in bots]
    return "\n".join(bot_names)


def create_bot_filter(text, user, channel):
    pattern = r'\A<[^>]*> create bot (\S+)'
    result = re.match(pattern, text)
    if not result:
        return text
    bot_name = result.group(1)
    session = Session()
    same_name_bot = session.query(Bot).filter(
        Bot.name == bot_name).first()
    if same_name_bot:
        raise Exception(f"error: bot {bot_name} exists")
    first_template = session.query(Template).order_by(Template.id).first()
    if first_template is None:
        raise Exception("error: templates does not defined")
    template_id = first_template.id
    new_bot = Bot(
        name=bot_name,
        channel_id=channel,
        tones="ラッパーの口調,default,幼い子供の口調",
        keywords="バックエンド,フロントエンド,セキュリティ",
        template_id=template_id,
        frequency="24h",
        start_from=datetime.datetime.now(),
        owner_slack_id=user
    )
    session.add(new_bot)
    session.commit()
    return f"bot {bot_name} created"


def set_template_to_bot_filter(text, user, channel):
    pattern = r'\A<[^>]*> set template (\S+) ?(\S[\s\S]*)\Z'
    result = re.match(pattern, text)
    if not result:
        return text
    bot_name = result.group(1)
    session = Session()
    bot = session.query(Bot).filter(
        Template.name == bot_name).first()
    if not bot:
        raise Exception(f"error: template {bot_name} not found")
    if not result.group(2):
        raise Exception("error: bad request missing template text")
    template_name = result.group(2)
    template = session.query(Template).filter(
        Template.name == template_name).first()
    if not template:
        raise Exception(f"error: template {template_name} not found")
    bot.template_id = template.id
    session.add(bot)
    session.commit()
    return f"bot {bot_name} updated"


def create_template_filter(text, user, channel):
    pattern = r'\A<[^>]*> create template (\S+) ?(\S[\s\S]*)?\Z'
    result = re.match(pattern, text)
    if not result:
        return text
    template_name = result.group(1)
    session = Session()
    same_name_template = session.query(Template).filter(
        Template.name == template_name).first()
    if same_name_template:
        raise Exception(f"error: template {template_name} exists")
    print(result.group(1))
    template_text = result.group(2) if result.group(2) else ""
    new_template = Template(
        name=template_name,
        text=template_text,
        owner_slack_id=user
    )
    session.add(new_template)
    session.commit()
    return f"template {template_name} created"


def set_template_filter(text, user, channel):
    pattern = r'\A<[^>]*> set template (\S+) ?(\S[\s\S]*)?\Z'
    result = re.match(pattern, text)
    if not result:
        return text
    template_name = result.group(1)
    session = Session()
    template = session.query(Template).filter(
        Template.name == template_name).first()
    if not template:
        raise Exception(f"error: template {template_name} not found")
    if not result.group(2):
        raise Exception("error: bad request missing template text")
    template.text = result.group(2)
    session.add(template)
    session.commit()
    return f"template {template_name} updated"


@app.event("message")
def handle_message_events(body, logger):
    logger.info(body)


if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
