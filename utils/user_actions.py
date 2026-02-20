import locale
from datetime import timedelta, datetime
from aiogram import Bot
from aiogram.types import User

from bot_config import texts, config, prices
from config import TOKEN, ADMIN
from utils.channels import find_channel_name, Channel, CHANNELS_BY_CHAT
from utils.database import set_inactive, get_payment


locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')


def get_link(user_id: int | str, user_name: str) -> str:
    return f'<a href="tg://user?id={user_id}">{user_name}</a>'


def get_date(date: str):
    return datetime.strptime(date, '%Y-%m-%d %H:%M:%S')


def format_date(date: str):
    return f'{get_date(date):%d %B в %H:%M}' if date else 'Никогда'


async def send_mess(bot: Bot, chat: int | str, text: str, kb=None):
    await bot.send_message(chat_id=chat, text=text, reply_markup=kb, parse_mode='HTML')


def format_sub(sub, channel: Channel = None):
    if not channel:
        channel = CHANNELS_BY_CHAT[int(sub['channel'])]
    clean_id = str(channel.chat_id)[4:]
    dates = [format_date(sub[f'{date}_date']) for date in ('start', 'end')]
    price_info = prices.get(sub['period'])
    return texts.get('about_sub').format(clean_id, channel.name, price_info['period'], price_info['cost'], *dates)


async def remove_user(user_id: int | str, user_name: str, channel_id: int):
    admin_text = format_event_message('ban', channel_id, user_id=user_id, user_name=user_name)
    subs = set_inactive(user_id, channel_id)
    if subs:
        sub = get_payment(subs[0]['id'])
        admin_text += '\n\n' + format_sub(sub)
    async with Bot(token=TOKEN) as bot:
        await send_mess(bot, ADMIN, admin_text)
        await send_mess(bot, user_id, texts.get('sub_expired').format(find_channel_name(channel_id)),
                        config.keyboards.get(channel_id))
        await bot.ban_chat_member(chat_id=channel_id, user_id=user_id)


async def notify_user(user_id: int | str, channel_id: int):
    channel_name = find_channel_name(channel_id)
    async with Bot(token=TOKEN) as bot:
        await send_mess(bot, user_id, texts.get('user_notify').format(channel_name), config.keyboards.get(channel_id))


async def create_invite(bot: Bot, chat: int, user: str) -> str:
    invite_link = await bot.create_chat_invite_link(chat_id=chat, name=f'bot_{user}', member_limit=1,
                                                    expire_date=timedelta(days=6))
    return invite_link.invite_link


def format_event_message(action: str, chat: int, user: User = None, user_id: int = None, user_name: str = None):
    if user:
        user_id, user_name = user.id, user.first_name
    return texts.get(f'user_{action}').format(get_link(user_id, user_name), find_channel_name(chat))
