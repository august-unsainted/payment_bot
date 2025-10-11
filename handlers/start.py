from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, User, ChatMemberUpdated
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot_config import config, db, prices, format_price
from bot_constructor.utils_funcs import get_btn

from config import ADMIN, OWNER, CHANNEL, TOKEN

jobstores = {'default': SQLAlchemyJobStore(url=f'sqlite:///{Path().cwd() / 'data/bot.db'}')}
scheduler = AsyncIOScheduler(timezone='Asia/Irkutsk', jobstores=jobstores)
router = Router()


class PayStates(StatesGroup):
    pay = State()


async def remove_user(user_id: int | str):
    async with Bot(token=TOKEN) as bot:
        await bot.ban_chat_member(chat_id=CHANNEL, user_id=user_id)


def schedule_remove(user_id: int | str, date: str):
    scheduler.add_job(id=str(user_id), trigger='date', run_date=datetime.strptime(date, '%Y-%m-%d %H:%M'),
                      func=remove_user, args=[user_id], replace_existing=True)


def get_user_link(user: User) -> str:
    return f'<a href="tg://user?id={user.id}">{user.username or user.first_name}</a>'


@router.callback_query(F.data.in_(('week', 'month', 'forever')))
async def get_price(callback: CallbackQuery):
    message = deepcopy(config.messages.get('price'))
    period, price, days = prices.get(callback.data).values()
    price = format_price(price)
    message['text'] = message['text'].format(period, price)
    btn = message['reply_markup'].inline_keyboard[0][0]
    btn.text, btn.callback_data = btn.text.format(price), f'pay_{callback.data}'
    await config.handle_message(callback, message)


@router.callback_query(F.data.startswith('pay'))
async def get_pay_requisites(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split('_')[-1]
    kb = InlineKeyboardMarkup(inline_keyboard=[[get_btn(category)]])
    await config.handle_message(callback, {'text': config.texts.get('pay'), 'reply_markup': kb})
    await state.update_data(message=callback.message.message_id, category=category)
    await state.set_state(PayStates.pay)


@router.message(PayStates.pay)
async def forward_pay(message: Message, state: FSMContext):
    data = await state.get_data()
    args = {'chat_id': message.chat.id, 'message_id': data.get('message'), 'parse_mode': 'HTML'}
    if not (message.document or message.photo):
        answer = config.texts.get('pay') + '\n\n' + config.texts.get('type_validation_error')
        kb = InlineKeyboardMarkup(inline_keyboard=[[get_btn(data.get('category'))]])
        await state.set_state(PayStates.pay)
        await message.delete()
        await message.bot.edit_message_text(text=answer, reply_markup=kb, **args)
        return
    await state.clear()
    user = message.from_user
    query = 'insert into payments (user_id, sum, period) values (?, ?, ?)'
    period, cost, days = prices.get(data.get('category')).values()
    payment_id = db.execute_query(query, user.id, cost, days)
    kb = config.edit_keyboard(f'{payment_id}_{user.id}', 'check_pay')
    info = config.texts.get('check_pay').format(get_user_link(user), period, format_price(cost))
    caption = info + f'\n\n<blockquote>{message.caption or ''}</blockquote>'
    await message.copy_to(chat_id=ADMIN, reply_markup=kb, parse_mode='HTML', caption=caption)
    await message.delete()
    await message.bot.edit_message_text(text=config.texts.get('pay_process'), **args)


@router.callback_query(F.data.startswith(('accept', 'reject')))
async def answer_pay(callback: CallbackQuery):
    action, pay_id, user = callback.data.split('_')
    accepted = action == 'accept'
    db.execute_query('update payments set status = ? where id = ?', action + 'ed', pay_id)
    kb = config.keyboards.get(f'pay_{action}')
    btn = kb.inline_keyboard[0][0]
    if accepted:
        await callback.bot.unban_chat_member(chat_id=CHANNEL, user_id=callback.from_user.id, only_if_banned=True)
        invite_link = await callback.bot.create_chat_invite_link(chat_id=CHANNEL, name=f'bot_{user}', member_limit=1,
                                                                 expire_date=timedelta(days=6))
        btn.url = invite_link.invite_link
    else:
        btn.url = f'tg://user?id={OWNER}'
    await callback.bot.send_message(chat_id=user, text=config.texts.get(f'pay_{action}'), reply_markup=kb)
    text = callback.message.caption or ''
    status = 'принят' if accepted else 'отклонен'
    await callback.message.edit_caption(caption=text + f'\n\nПлатеж {status}!')


@router.callback_query(F.data == 'promo')
async def get_promo(callback: CallbackQuery, state: FSMContext):
    pass


@router.chat_member(F.chat.id == CHANNEL and
                    F.old_chat_member.status == 'left' and F.new_chat_member.status == "member")
async def chat_member_updated(event: ChatMemberUpdated):
    user = event.new_chat_member.user
    query = '''
    update payments set start_date = ?, end_date = datetime(?, '+' || period || ' days')
    where user_id = ? and start_date is NULL and status = "accepted"
    returning end_date
    '''
    start_date = f'{datetime.now():%F %T}'
    result = db.execute_query(query, start_date, start_date, user.id)
    if not result:
        await remove_user(user.id)
        return
    end_date = result[0]['end_date']
    schedule_remove(user.id, end_date)
    text = config.texts.get('user_join').format(get_user_link(user))
    await event.bot.send_message(chat_id=ADMIN, text=text, parse_mode='HTML')
