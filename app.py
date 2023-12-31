import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import chatgpt
import re
import datetime
import random
import traceback

from sqlalchemy.orm import sessionmaker
from database import engine
from models import Bot, Template
import schedule
import threading
import time

load_dotenv()

app = App(token=os.environ.get("SLACK_BOT_TOKEN"))
Session = sessionmaker(bind=engine)
jobs = {}


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
        text = delete_bot_filter(text, user, channel)
        text = set_template_to_bot_filter(text, user, channel)
        text = set_tones_to_bot_filter(text, user, channel)
        text = set_keywords_to_bot_filter(text, user, channel)
        text = set_frequency_to_bot_filter(text, user, channel)
        text = create_template_filter(text, user, channel)
        text = delete_template_filter(text, user, channel)
        text = set_template_filter(text, user, channel)
        text = show_templates_filter(text, user, channel)
        text = show_bots_filter(text, user, channel)
        text = run_bot_filter(text, user, channel)
    except Exception as e:
        text = str(e)
        traceback.print_exc()
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
        tones="default,ラッパーの口調,幼い子供の口調,吟遊詩人の口調,老人の口調,語尾が「ぴょん」の口調",
        keywords="バックエンド,フロントエンド,セキュリティ",
        template_id=template_id,
        frequency="daily",
        start_from=datetime.datetime.now(),
        owner_slack_id=user
    )
    session.add(new_bot)
    session.commit()
    jobs[new_bot.name] = add_bot_in_schedule(new_bot)
    return f"bot {bot_name} created"


def set_template_to_bot_filter(text, user, channel):
    pattern = r'\A<[^>]*> set (\S+) template (\S+)\Z'
    result = re.match(pattern, text)
    if not result:
        return text
    bot_name = result.group(1)
    session = Session()
    bot = session.query(Bot).filter(
        Bot.name == bot_name).first()
    if not bot:
        raise Exception(f"error: template {bot_name} not found")
    if not result.group(2):
        raise Exception("error: bad request missing template text")
    if bot.owner_slack_id != user:
        raise Exception("error: permission error")
    template_name = result.group(2)
    template = session.query(Template).filter(
        Template.name == template_name).first()
    if not template:
        raise Exception(f"error: template {template_name} not found")
    bot.template_id = template.id
    session.add(bot)
    session.commit()
    return f"bot {bot_name} template updated"


def set_frequency_to_bot_filter(text, user, channel):
    pattern = r'\A<[^>]*> set (\S+) frequency (\S+)\Z'
    result = re.match(pattern, text)
    if not result:
        return text
    bot_name = result.group(1)
    session = Session()
    bot = session.query(Bot).filter(
        Bot.name == bot_name).first()
    if not bot:
        raise Exception(f"error: template {bot_name} not found")
    if not result.group(2):
        raise Exception("error: bad request missing frequency text")
    if bot.owner_slack_id != user:
        raise Exception("error: permission error")
    frequency = result.group(2)
    bot.frequency = frequency
    session.add(bot)
    session.commit()
    if bot.name in jobs.keys():
        schedule.clear(jobs[bot.name])
        jobs[bot.name] = add_bot_in_schedule(bot)
    return f"bot {bot_name} frequency updated"


def set_keywords_to_bot_filter(text, user, channel):
    pattern = r'\A<[^>]*> set (\S+) keywords (\S+)\Z'
    result = re.match(pattern, text)
    if not result:
        return text
    bot_name = result.group(1)
    session = Session()
    bot = session.query(Bot).filter(
        Bot.name == bot_name).first()
    if not bot:
        raise Exception(f"error: template {bot_name} not found")
    if not result.group(2):
        raise Exception("error: bad request missing keywords text")
    if bot.owner_slack_id != user:
        raise Exception("error: permission error")
    keywords = result.group(2)
    bot.keywords = keywords
    session.add(bot)
    session.commit()
    return f"bot {bot_name} keywords updated"


def set_tones_to_bot_filter(text, user, channel):
    pattern = r'\A<[^>]*> set (\S+) tones (\S+)\Z'
    result = re.match(pattern, text)
    if not result:
        return text
    bot_name = result.group(1)
    session = Session()
    bot = session.query(Bot).filter(
        Bot.name == bot_name).first()
    if not bot:
        raise Exception(f"error: template {bot_name} not found")
    if not result.group(2):
        raise Exception("error: bad request missing tones text")
    if bot.owner_slack_id != user:
        raise Exception("error: permission error")
    tones = result.group(2)
    bot.tones = tones
    session.add(bot)
    session.commit()
    return f"bot {bot_name} tones updated"


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


def run_bot_filter(text, user, channel):
    pattern = r'\A<[^>]*> run (\S+)'
    result = re.match(pattern, text)
    if not result:
        return text
    bot_name = result.group(1)
    session = Session()
    bot = session.query(Bot).filter(
        Bot.name == bot_name).first()
    if not bot:
        raise Exception(f"error: bot {bot_name} not found")
    text = bot_run(bot)
    return text


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


def bot_run(bot):
    session = Session()
    template = session.query(Template).filter(
        Template.id == bot.template_id).first()
    prompt = template.text
    keyword = random.choice(bot.keywords.split(","))
    prompt = prompt.replace("[keyword]", keyword)
    messages = chatgpt.chat(prompt, return_messages=True)
    print("tones", bot.tones.split(","))
    tone = random.choice(bot.tones.split(","))
    res = convert_tone(messages, tone)
    return res


def bot_run_post(bot):
    res = bot_run(bot)
    app.client.chat_postMessage(
        channel=bot.channel_id,  # 送信先のチャンネルID
        text=res  # 送信するメッセージ
    )
    return res


def convert_tone(messages, tone):
    print("messages", messages)
    print("tone", tone)
    if tone == "default":
        print("default tone res", messages[-1]["content"])
        return messages[-1]["content"]
    prompt = f"上の日本語を{tone}に変換してください"
    return chatgpt.chat(text=prompt, messages_log=messages)


@app.event("message")
def handle_message_events(body, logger):
    logger.info(body)


def schedule_tasks():
    session = Session()
    bots = session.query(Bot).order_by(Bot.id)
    for bot in bots:
        jobs[bot.name] = add_bot_in_schedule(bot)
    while True:
        schedule.run_pending()
        time.sleep(1)


def add_bot_in_schedule(bot):
    if bot.frequency == "daily":
        start_from = bot.start_from.strftime("%H:%M")
        return schedule.every().day.at(start_from).do(lambda: bot_run_post(bot))
    frequency = int(bot.frequency[:-1])
    unit = bot.frequency[-1]

    if unit == "s":
        return schedule.every(frequency).seconds.do(lambda: bot_run_post(bot))
    if unit == "m":
        return schedule.every(frequency).minutes.do(lambda: bot_run_post(bot))
    if unit == "h":
        return schedule.every(frequency).hours.do(lambda: bot_run_post(bot))


if __name__ == "__main__":
    schedule_thread = threading.Thread(target=schedule_tasks)
    schedule_thread.start()
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
