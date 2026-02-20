from aiogram import Router, F
from aiogram.types import CallbackQuery

from bot_config import texts, config
from utils.channels import CHANNELS
from utils.database import get_active_sub
from utils.user_actions import format_date

router = Router()


@router.callback_query(F.data == 'subscriptions')
async def handle_subs(callback: CallbackQuery):
    user_id = callback.from_user.id
    args = config.messages.get('subscriptions').copy()
    for channel in CHANNELS:
        sub = get_active_sub(user_id, channel.chat_id)
        if not sub:
            continue
        clean_id = str(channel.chat_id)[4:]
        dates = [format_date(sub[f'{date}_date']) for date in ('end', 'start')]
        args['text'] += '\n\n' + texts.get('about_sub').format(clean_id, channel.name, *dates)

    if '\n\n' not in args['text']:
        args['text'] += texts.get('none_sub')
    await callback.message.answer(**args)
    await callback.message.delete()
