from copy import deepcopy
from bot_constructor.bot_config import BotConfig

from config import PHOTO
from utils.channels import CHANNELS

config = BotConfig(name_in_start=True)
db = config.db
prices = config.jsons['price']


def format_price(price: int) -> str:
    formatted = f"{price:,}".replace(',', ' ')
    return formatted


def generate_price_kb(channel_name: str):
    data = {}
    for period, info in prices.items():
        key = f'pay_{period}_{channel_name}'
        data[key] = f'{info['period'].capitalize()} — {format_price(info['cost'])}₽'
    kb = config.generate_kb('start', data)
    return kb


def load_keyboards():
    for channel in CHANNELS:
        kb = generate_price_kb(channel.callback)
        config.keyboards[channel.callback] = deepcopy(kb)
        del kb.inline_keyboard[-1]
        config.keyboards[channel.chat_id] = kb


load_keyboards()
config.load_messages()
config.test_mode = True
config.messages['start']['media'].media = config.messages['cmd_start']['photo'] = PHOTO
texts = config.texts
