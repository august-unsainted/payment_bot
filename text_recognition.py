import asyncio
import base64

from openai import OpenAI, RateLimitError, AsyncOpenAI
from pathlib import Path

from config import AI_KEY, SYSTEM_PROMPT, AI_MODEL

sleep = 5
max_retries = 3
timeout = 60
file_dir = Path().cwd() / 'data/images'
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=AI_KEY)


def generate_content(file: bytes, is_file: bool) -> dict[str, str]:
    file_data = base64.b64encode(file).decode('utf-8')
    file_type = 'pdf' if is_file else 'jpeg'
    types = ['application', 'file'] if is_file else ['image', 'image_url']
    url = f"data:{types[0]}/{file_type};base64,{file_data}"
    content = {"filename": "document.pdf", "file_data": url} if is_file else {"url": url}
    return {"type": types[1], types[1]: content}


async def send_ai_request(file: bytes, is_file: bool) -> str | None:
    for attempt in range(max_retries):
        data = generate_content(file, is_file)
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
            if isinstance(err, asyncio.TimeoutError):
                err = 'вышло время ожидания'
            print(f"Ошибка: {err}, попытка {attempt + 1}/{max_retries}.")
            await asyncio.sleep(sleep)
            continue
    return None


# for _, _, filenames in file_dir.walk():
#     for filename in filenames:
#         print(send_ai_request(filename))
