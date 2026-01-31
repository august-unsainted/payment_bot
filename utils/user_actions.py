from datetime import timedelta

from aiogram import Bot

from bot_config import texts, config
from config import TOKEN, ADMIN
from utils.database import set_inactive

start_kb = config.keyboards.get('start')


def get_link(user_id: int | str, user_name: str) -> str:
    return f'<a href="tg://user?id={user_id}">{user_name}</a>'


async def send_mess(bot: Bot, chat: int | str, text: str, kb=None):
    await bot.send_message(chat_id=chat, text=text, reply_markup=kb, parse_mode='HTML')


async def remove_user(user_id: int | str, user_name: str, channel_id: int):
    set_inactive(user_id, channel_id)
    async with Bot(token=TOKEN) as bot:
        admin_text = texts.get('user_ban').format(get_link(user_id, user_name))
        await send_mess(bot, ADMIN, admin_text)
        await send_mess(bot, user_id, texts.get('sub_expired'), start_kb)
        await bot.ban_chat_member(chat_id=channel_id, user_id=user_id)


async def notify_user(user_id: int | str):
    async with Bot(token=TOKEN) as bot:
        await send_mess(bot, user_id, texts.get('user_notify'), start_kb)


async def create_invite(bot: Bot, chat: int, user: str) -> str:
    invite_link = await bot.create_chat_invite_link(chat_id=chat, name=f'bot_{user}', member_limit=1,
                                                    expire_date=timedelta(days=6))
    return invite_link.invite_link
