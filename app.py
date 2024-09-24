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
from patterns import Patterns
import pprint

load_dotenv()

app = App(token=os.environ.get("SLACK_BOT_TOKEN"))
Session = sessionmaker(bind=engine)
jobs = {}
ptns = Patterns()


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
        text = easily_create_bot_filter(text, user, channel)
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
        text = show_bot_filter(text, user, channel)
        text = show_jobs_filter(text, user, channel)
        text = run_bot_filter(text, user, channel)
        text = help_filter(text, user, channel)
        text = not_found_filter(text, user, channel)
    except Exception as e:
        text = str(e)
        traceback.print_exc()
    say(
        text=text
    )

def not_found_filter(text, user, channel):
    pattern = r'\A<[^>]*>'
    result = re.match(pattern, text)
    if not result:
        return text
    return "command not found"

def help_filter(text, user, channel):
    pattern = ptns.help_pattern
    result = re.match(pattern, text)
    if not result:
        return text
    help_pattern_docs = "\n".join([f"{key}: {str(value).replace('<[^>]*>','@botgpt')}" for key, value in Patterns.__dict__.items() if key.endswith('_pattern')])
    return f"help \n {help_pattern_docs}"

def delete_template_filter(text, user, channel):
    pattern = ptns.delete_template_pattern
    result = re.match(pattern, text)
    if not result:
        return text
    template_name = result.group(1)
    with Session() as session:
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
    pattern = ptns.delete_bot_pattern
    result = re.match(pattern, text)
    if not result:
        return text
    bot_name = result.group(1)
    with Session() as session:
        bot = session.query(Bot).filter(
            Bot.name == bot_name).first()
        if not bot:
            raise Exception(f"error: bot {bot_name} not found")
        if bot.owner_slack_id != user:
            raise Exception("error: permission error")
        if bot.name in jobs.keys():
            schedule.clear(bot.name)
        session.delete(bot)
        session.commit()
    print("delete job",jobs)
    return f"bot {bot_name} deleted"


def show_templates_filter(text, user, channel):
    pattern = ptns.show_templates_pattern
    result = re.match(pattern, text)
    if not result:
        return text
    with Session() as session:
        templates = session.query(Template).order_by(Template.id)
    template_names = [template.name for template in templates]
    return "\n".join(template_names)


def show_jobs_filter(text, user, channel):
    pattern = ptns.show_jobs_pattern
    result = re.match(pattern, text)
    if not result:
        return text
    return pprint.pformat(jobs)

def show_bots_filter(text, user, channel):
    pattern = ptns.show_bots_pattern
    result = re.match(pattern, text)
    if not result:
        return text
    with Session() as session:
        bots = session.query(Bot).order_by(Bot.id)
    bot_infos = [f"name: {bot.name} channel: <#{bot.channel_id}> frequency: {bot.frequency}" for bot in bots]
    return "\n".join(bot_infos)


def show_bot_filter(text, user, channel):
    pattern = ptns.show_bot_pattern
    result = re.match(pattern, text)
    if not result:
        return text
    bot_name = result.group(1)
    with Session() as session:
        bot = session.query(Bot).filter(
            Bot.name == bot_name).first()
    if not bot:
        raise Exception(f"error: bot {bot_name} not found")
    template = session.query(Template).filter(
            Template.id == bot.template_id).first()
    bot_infos = f"name: {bot.name}\n\
    channel: <#{bot.channel_id}>\n\
    tones: {bot.tones}\n\
    keywords: {bot.keywords}\n\
    template_id: {bot.template_id}\n\
    frequency: {bot.frequency}\n\
    owner: <@{bot.owner_slack_id}>"
    if template:
        bot_infos += f"template: \n\
            name: {template.name}\n\
            text: {template.text}\n"
    return bot_infos



def create_bot_filter(text, user, channel):
    pattern = ptns.create_bot_pattern
    result = re.match(pattern, text)
    if not result:
        return text
    bot_name = result.group(1)
    with Session() as session:
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


def easily_create_bot_filter(text, user, channel):
    pattern = ptns.easily_create_bot_pattern
    result = re.match(pattern, text)
    if not result:
        return text
    bot_name = result.group('bot_name')
    with Session() as session:
        same_name_bot = session.query(Bot).filter(
            Bot.name == bot_name).first()
        if same_name_bot:
            raise Exception(f"error: bot {bot_name} exists")
        template_name = bot_name + "_template"
        same_name_template = session.query(Template).filter(
            Template.name == template_name).first()
        if same_name_template:
            raise Exception(f"error: template {template_name} exists")
        template_text = result.group('template_text') if result.group('template_text') else ""
        new_template = Template(
            name=template_name,
            text=template_text,
            owner_slack_id=user
        )
        session.add(new_template)
        session.flush()
        new_bot = Bot(
            name=bot_name,
            channel_id=channel,
            tones="default,ラッパーの口調,幼い子供の口調,吟遊詩人の口調,老人の口調,語尾が「ぴょん」の口調",
            keywords="バックエンド,フロントエンド,セキュリティ",
            template_id=new_template.id,
            frequency="daily",
            start_from=datetime.datetime.now(),
            owner_slack_id=user
        )
        session.add(new_bot)
        session.commit()
        jobs[new_bot.name] = add_bot_in_schedule(new_bot)
    return f"bot {bot_name} created"


def set_template_to_bot_filter(text, user, channel):
    pattern = ptns.set_template_to_bot_pattern
    result = re.match(pattern, text)
    if not result:
        return text
    bot_name = result.group(1)
    with Session() as session:
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
    pattern = ptns.set_frequency_to_bot_pattern
    result = re.match(pattern, text)
    if not result:
        return text
    bot_name = result.group(1)
    with Session() as session:
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

        if bot_name in jobs.keys():
            schedule.clear(bot_name)
            jobs[bot_name] = add_bot_in_schedule(bot)
    return f"bot {bot_name} frequency updated"


def set_keywords_to_bot_filter(text, user, channel):
    pattern = ptns.set_keywords_to_bot_pattern
    result = re.match(pattern, text)
    if not result:
        return text
    bot_name = result.group(1)
    with Session() as session:
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
    pattern = ptns.set_tones_to_bot_pattern
    result = re.match(pattern, text)
    if not result:
        return text
    bot_name = result.group(1)
    with Session() as session:
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
    pattern = ptns.create_template_pattern
    result = re.match(pattern, text)
    if not result:
        return text
    template_name = result.group(1)
    with Session() as session:
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
    pattern = ptns.run_bot_pattern
    result = re.match(pattern, text)
    if not result:
        return text
    bot_name = result.group(1)
    with Session() as session:
        bot = session.query(Bot).filter(
            Bot.name == bot_name).first()
    if not bot:
        raise Exception(f"error: bot {bot_name} not found")
    text = bot_run(bot)
    return text


def set_template_filter(text, user, channel):
    pattern = ptns.set_template_pattern
    result = re.match(pattern, text)
    if not result:
        return text
    template_name = result.group(1)
    with Session() as session:
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
    with Session() as session:
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


def bot_run_post(bot_id):
    with Session() as session:
        bot = session.query(Bot).filter(
        Bot.id == bot_id).first()
        channel_id=bot.channel_id
    res = bot_run(bot)
    app.client.chat_postMessage(
        channel=channel_id,  # 送信先のチャンネルID
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
    with Session() as session:
        bots = session.query(Bot).order_by(Bot.id)
        for bot in bots:
            jobs[bot.name] = add_bot_in_schedule(bot)
    while True:
        schedule.run_pending()
        time.sleep(1)


def add_bot_in_schedule(bot):
    if bot.frequency == "never":
        return
    if bot.frequency == "daily":
        start_from = bot.start_from.strftime("%H:%M")
        return schedule.every().day.at(start_from).do(lambda: bot_run_post(bot.id)).tag(bot.name)
    frequency = int(bot.frequency[:-1])
    unit = bot.frequency[-1]

    if unit == "s":
        return schedule.every(frequency).seconds.do(lambda: bot_run_post(bot.id)).tag(bot.name)
    if unit == "m":
        return schedule.every(frequency).minutes.do(lambda: bot_run_post(bot.id)).tag(bot.name)
    if unit == "h":
        return schedule.every(frequency).hours.do(lambda: bot_run_post(bot.id)).tag(bot.name)
    if unit == "d":
        return schedule.every(frequency).days.do(lambda: bot_run_post(bot.id)).tag(bot.name)


if __name__ == "__main__":
    schedule_thread = threading.Thread(target=schedule_tasks)
    schedule_thread.start()
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
