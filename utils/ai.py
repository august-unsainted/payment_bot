import fitz
import asyncio
import base64

from aiogram.types import Message, BufferedInputFile
from openai import OpenAI, RateLimitError
from pathlib import Path

from config import AI_KEY, SYSTEM_PROMPT, AI_MODEL

sleep = 5
max_retries = 3
timeout = 60
file_dir = Path().cwd() / 'data/images'
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=AI_KEY)


def convert_file(file: bytes, message: Message):
    message_file = message.photo[-1] if message.photo else message.document
    if not message.document:
        return message_file.file_id
    doc = fitz.open(stream=file, filetype="pdf")
    image_bytes = doc.load_page(0).get_pixmap(dpi=150).tobytes()
    return BufferedInputFile(file=image_bytes, filename='check.png')


def generate_content(file: bytes) -> dict[str, str]:
    file_data = base64.b64encode(file).decode('utf-8')
    url = f"data:image/jpeg;base64,{file_data}"
    return {'type': 'image_url', 'image_url': {"url": url}}


async def send_ai_request(file: bytes) -> str | None:
    error = 'Вышло время ожидания'
    for attempt in range(max_retries):
        data = generate_content(file)
        try:
            completion = client.chat.completions.create(
                model=AI_MODEL,
                messages=[
                    {"role": "user", "content": [{"type": "text", "text": SYSTEM_PROMPT}, data]}
                ])
            answer = completion.choices[0].message.content
            return answer
        except RateLimitError:
            return f'Ошибка: закончились запросы.'
        except Exception as err:
            print(f"Ошибка: {err}, попытка {attempt + 1}/{max_retries}.")
            error = err.args[0][:100] + '...'
            await asyncio.sleep(sleep)
            continue
    return error
