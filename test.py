from sqlalchemy.orm import sessionmaker
from database import engine 
from models import Bot, Template
# SQLAlchemyセッションを作成します。
Session = sessionmaker(bind=engine)
session = Session()
new_template = Template(
    name="test_template",
    text="This is a test template.",
    owner_slack_id="U1234"
)
session.add(new_template)
session.commit()
# Botを作成してデータベースに追加します。
new_bot = Bot(
    name="test_bot",
    channel_id=12345,
    tones="ラッパーの口調,default,幼い子供の口調",
    keywords="バックエンド,フロントエンド,セキュリティ",
    template_id=new_template.id,
    frequency="daily",
    start_from="2023-07-01",
    owner_slack_id="U1234"
)
session.add(new_bot)
session.commit()

# 作成したBotを取得します。
bot = session.query(Bot).filter(Bot.name == "test_bot").first()
print(bot.name)

# Botの情報を更新します。
bot.channel_id = 67890
session.commit()

# 更新されたBotの情報を確認します。
updated_bot = session.query(Bot).filter(Bot.name == "test_bot").first()
print(updated_bot.channel_id)

# Botを削除します。
session.delete(updated_bot)
session.commit()

# 削除されたことを確認します。
deleted_bot = session.query(Bot).filter(Bot.name == "test_bot").first()
print(deleted_bot)  # Noneが表示されるべきです
