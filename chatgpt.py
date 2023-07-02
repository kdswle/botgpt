
from dotenv import load_dotenv
import os
import openai
# .envファイルから環境変数を読み込む
load_dotenv()

openai.organization = os.getenv("OPENAI_ORGANIZATION_ID")
openai.api_key = os.getenv("OPENAI_API_KEY")
print(os.getenv("OPENAI_ORGANIZATION_ID"))
MODEL = "gpt-4"


def chat(text):
    response = openai.ChatCompletion.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "あなたはアシスタントです。"},
            {"role": "user", "content": text},
        ],
        temperature=0,
    )
    return response.choices[0].message.content

    print(response.choices[0].message.content)
