from copy import deepcopy
from datetime import datetime

from bot_constructor.bot_config import BotConfig

config = BotConfig(name_in_start=True)
db = config.db
prices = config.jsons['price']


def format_price(price: int) -> str:
    formatted = f"{price:,}".replace(',', ' ')
    return formatted


def generate_price_kb():
    data = {}
    for period, info in prices.items():
        data[period] = f'{info['period'].capitalize()} — {format_price(info['cost'])}₽'
    kb = config.generate_kb(None, data)
    return kb


def load_price_messages():
    template = deepcopy(config.messages.get('price'))
    for key, data in prices.items():
        period, price, days = data.values()
        price = format_price(price)
        config.texts[key] = template['text'].format(period, price)
        kb = deepcopy(template.get('reply_markup'))
        btn = kb.inline_keyboard[0][0]
        btn.text, btn.callback_data = btn.text.format(price), f'pay_{key}'
        config.keyboards[key] = kb


config.keyboards['start'] = generate_price_kb()
load_price_messages()
config.load_messages()
config.test_mode = True
texts = config.texts
