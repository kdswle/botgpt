from sqlalchemy import create_engine
from models import Base
from dotenv import load_dotenv
import os

# .envファイルから環境変数を読み込む
load_dotenv()

username = os.getenv('DB_USERNAME')
password = os.getenv('DB_PASSWORD')
host = os.getenv('DB_HOST')
dbname = os.getenv('DB_NAME')

# DB接続用のエンジンを作成
engine = create_engine(f'postgresql://{username}:{password}@{host}/{dbname}')
Base.metadata.create_all(engine)
