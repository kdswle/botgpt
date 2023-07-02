
from dotenv import load_dotenv
import os
import openai
# .envファイルから環境変数を読み込む
load_dotenv()

openai.organization = os.getenv("OPENAI_ORGANIZATION_ID")
openai.api_key = os.getenv("OPENAI_API_KEY")
print(os.getenv("OPENAI_ORGANIZATION_ID"))
MODEL = "gpt-4"


def chat(text, messages_log=[], return_messages=False):
    messages = messages_log + [{"role": "user", "content": text}]
    response = openai.ChatCompletion.create(
        model=MODEL,
        messages=messages,
        temperature=0.7,
    )
    if not return_messages:
        return response.choices[0].message.content
    new_messages = messages \
        + [{
            "role": "assistant",
            "content": response.choices[0].message.content
        }]

    return new_messages
