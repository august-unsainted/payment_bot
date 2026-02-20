import locale
from datetime import datetime

locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')


def get_date(date: str):
    return datetime.strptime(date, '%Y-%m-%d %H:%M:%S')


def format_date(date: str):
    return f'{get_date(date):%d %B в %H:%M}' if date else 'Никогда'
