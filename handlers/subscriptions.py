from aiogram import Router, F
from aiogram.types import CallbackQuery

from bot_config import texts, config
from config import CHANNELS, CHANNELS_NAMES
from utils.database import get_active_sub
from utils.user_actions import format_date

router = Router()


@router.callback_query(F.data == 'subscriptions')
async def handle_subs(callback: CallbackQuery):
    user_id = callback.from_user.id
    args = config.messages.get('subscriptions').copy()
    for data, chat in CHANNELS.items():
        sub = get_active_sub(user_id, chat)
        if not sub:
            continue
        channel = str(chat)[4:]
        dates = [format_date(sub[f'{date}_date']) for date in ('end', 'start')]
        args['text'] += '\n\n' + texts.get('about_sub').format(channel, CHANNELS_NAMES[data], *dates)

    if '\n\n' not in args['text']:
        args['text'] += texts.get('none_sub')
    await callback.message.answer(**args)
    await callback.message.delete()
