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


config.keyboards['start'] = generate_price_kb()
config.load_messages()
