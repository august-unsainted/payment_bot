from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery

from bot_config import config

router = Router()


@router.callback_query(F.data.in_(('week', 'month', 'forever')))
async def get_price(callback: CallbackQuery):
    message = config.messages.get('price')
    period, price = config.jsons['price'].get(callback.data)
    message['text'] = message['text'].format(period, price)
    message['reply_markup'].inline_keyboard[0][0].text = f'Оплатить {price}₽'
    await config.handle_message(callback, message)
