from aiogram import Router, F
from aiogram.types import CallbackQuery

from bot_config import texts, config
from utils.channels import CHANNELS
from utils.database import get_active_sub
from utils.user_actions import format_sub

router = Router()


@router.callback_query(F.data == 'subscriptions')
async def handle_subs(callback: CallbackQuery):
    user_id = callback.from_user.id
    args = config.messages.get('subscriptions').copy()
    subs = []
    for channel in CHANNELS:
        sub = get_active_sub(user_id, channel.chat_id)
        if not sub:
            continue
        subs.append(format_sub(sub, channel))

    args['text'] += '\n\n'.join(subs) if subs else texts.get('none_sub')
    await callback.message.answer(**args)
    await callback.message.delete()
