from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, ChatMemberUpdated, User
from bot_constructor.utils_funcs import get_btn

from bot_config import config, prices, format_price, texts
from config import ADMIN, CHANNELS, CHANNELS_NAMES
from utils.ai import convert_file, send_ai_request
from utils.database import insert_payment, update_status, get_payment
from utils.scheduler import activate_sub
from utils.user_actions import get_link, create_invite

router = Router()


class PayStates(StatesGroup):
    pay = State()


@router.callback_query(F.data.startswith('pay'))
async def get_requisites(callback: CallbackQuery, state: FSMContext):
    category, channel = callback.data.split('_')[1:]
    kb = InlineKeyboardMarkup(inline_keyboard=[[get_btn(category)]])
    await config.handle_message(callback, {'text': texts.get('pay'), 'reply_markup': kb})
    await state.clear()
    await state.update_data(message=callback.message.message_id, category=category, channel=channel)
    await state.set_state(PayStates.pay)


@router.message(PayStates.pay and F.text != '/start')
async def forward_pay(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    args = {'chat_id': message.chat.id, 'message_id': data.get('message'), 'parse_mode': 'HTML'}
    if not (message.document or message.photo):
        answer = texts.get('pay') + '\n\n' + texts.get('type_validation_error')
        kb = InlineKeyboardMarkup(inline_keyboard=[[get_btn(data.get('category'))]])
        await state.set_state(PayStates.pay)
        await message.delete()
        await bot.edit_message_text(text=answer, reply_markup=kb, **args)
        return

    await state.clear()
    user = message.from_user
    days, cost, period = prices.get(data.get('category')).values()
    channel = data.get('channel')
    payment_id = insert_payment(cost, period, user.id, CHANNELS[channel])
    kb = config.edit_keyboard(payment_id, 'check_pay')
    await bot.edit_message_text(text=texts.get('pay_process'), **args)
    await message.delete()

    message_file = message.photo[-1] if message.photo else message.document
    file = (await bot.download(file=message_file)).read()
    photo = convert_file(file, message)
    answer = await send_ai_request(file)

    user_link = get_link(user.id, user.first_name)
    info = texts.get('check_pay').format(user_link, days, CHANNELS_NAMES[channel], format_price(cost))
    caption = f'{info}\n{answer}\n\n<blockquote>{message.caption or ''}</blockquote>'
    await bot.send_photo(photo=photo, chat_id=ADMIN, reply_markup=kb, parse_mode='HTML', caption=caption)


@router.callback_query(F.data.startswith(('accept', 'reject')))
async def answer_pay(callback: CallbackQuery, bot: Bot):
    action, pay_id = callback.data.split('_')
    accepted = action == 'accept'
    update_status(action + 'ed', pay_id)
    pay = get_payment(pay_id)
    user_id, channel = pay['user_id'], pay['channel']

    kb = config.keyboards.get(f'pay_{action}' if accepted else 'to_start')
    if accepted:
        member = await bot.get_chat_member(channel, int(user_id))
        if member.status == 'member':
            user = await bot.get_chat(user_id)
            await activate_sub(user.id, user.first_name, channel, bot)
            kb = None
            action = 'extended'
        else:
            kb.inline_keyboard[0][0].url = await create_invite(bot, channel, user_id)
        await bot.unban_chat_member(chat_id=channel, user_id=user_id, only_if_banned=True)
    await bot.send_message(chat_id=user_id, text=texts.get(f'pay_{action}'), reply_markup=kb)
    text = callback.message.caption or ''
    status = 'принят' if accepted else 'отклонен'
    await callback.message.edit_caption(caption=text + f'\n\nПлатеж {status}!')


@router.callback_query(F.data == 'promo')
async def get_promo(callback: CallbackQuery, state: FSMContext):
    pass


@router.chat_member(F.chat.id.in_(CHANNELS.values()) and
                    F.old_chat_member.status == 'left' and F.new_chat_member.status == "member")
async def chat_member_updated(event: ChatMemberUpdated):
    user = event.new_chat_member.user
    await activate_sub(user.id, user.first_name, event.chat.id, event.bot)
