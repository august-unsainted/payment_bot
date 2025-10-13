from datetime import datetime, timedelta
from pathlib import Path

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, User, ChatMemberUpdated
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot_config import config, db, prices, format_price, texts
from bot_constructor.utils_funcs import get_btn

from config import ADMIN, OWNER, CHANNEL, TOKEN

jobstores = {'default': SQLAlchemyJobStore(url=f'sqlite:///{Path().cwd() / 'data/bot.db'}')}
scheduler = AsyncIOScheduler(timezone='Asia/Irkutsk', jobstores=jobstores)
router = Router()


class PayStates(StatesGroup):
    pay = State()


def get_link(user_id: str | int, name: str) -> str:
    return f'<a href="tg://user?id={user_id}">{name}</a>'


def get_user_link(user: User) -> str:
    name = f'@{user.username}' if user.username else user.first_name
    return get_link(user.id, name)


async def remove_user(user_id: int | str, user_name: str):
    db.execute_query('update payments set status = "inactive" where user_id = ? and status = "active"', user_id)
    async with Bot(token=TOKEN) as bot:
        admin_text = texts.get('user_ban').format(get_link(user_id, user_name))
        await bot.send_message(chat_id=ADMIN, text=admin_text, parse_mode='HTML')
        await bot.send_message(chat_id=user_id, text=texts.get('sub_expired'),
                               reply_markup=config.keyboards.get('start'), parse_mode='HTML')
        await bot.ban_chat_member(chat_id=CHANNEL, user_id=user_id)


async def notify_user(user_id: int | str):
    async with Bot(token=TOKEN) as bot:
        await bot.send_message(chat_id=user_id, text=texts.get('user_notify'),
                               reply_markup=config.keyboards.get('start'), parse_mode='HTML')


def schedule_jobs(user_id: int | str, user_name: str, date: str):
    end_date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
    delta = timedelta(seconds=30) if config.test_mode else timedelta(days=3)
    scheduler.add_job(id=f'{user_id}_notify', trigger='date', run_date=end_date - delta,
                      func=notify_user, args=[user_id], replace_existing=True)
    scheduler.add_job(id=str(user_id), trigger='date', run_date=end_date,
                      func=remove_user, args=[user_id, user_name], replace_existing=True)


@router.callback_query(F.data.startswith('pay'))
async def get_pay_requisites(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split('_')[-1]
    kb = InlineKeyboardMarkup(inline_keyboard=[[get_btn(category)]])
    await config.handle_message(callback, {'text': texts.get('pay'), 'reply_markup': kb})
    await state.update_data(message=callback.message.message_id, category=category)
    await state.set_state(PayStates.pay)


@router.message(PayStates.pay and F.text != '/start')
async def forward_pay(message: Message, state: FSMContext):
    data = await state.get_data()
    args = {'chat_id': message.chat.id, 'message_id': data.get('message'), 'parse_mode': 'HTML'}
    if not (message.document or message.photo):
        answer = texts.get('pay') + '\n\n' + texts.get('type_validation_error')
        kb = InlineKeyboardMarkup(inline_keyboard=[[get_btn(data.get('category'))]])
        await state.set_state(PayStates.pay)
        await message.delete()
        await message.bot.edit_message_text(text=answer, reply_markup=kb, **args)
        return
    await state.clear()
    user = message.from_user

    query = 'insert into payments (user_id, sum, period) values (?, ?, ?)'
    period, cost, days = prices.get(data.get('category')).values()
    prev_payments = db.execute_query('select id, period from payments where user_id = ? and status = "active"', user.id)
    if prev_payments:
        prev_pay = prev_payments[0]
        period += prev_pay['period']
        db.execute_query('update payments set status = "inactive" where id = ?', prev_pay['id'])
    payment_id = db.execute_query(query, user.id, cost, days)
    kb = config.edit_keyboard(f'{payment_id}_{user.id}', 'check_pay')
    info = texts.get('check_pay').format(get_user_link(user), period, format_price(cost))
    caption = info + f'\n\n<blockquote>{message.caption or ''}</blockquote>'
    await message.copy_to(chat_id=ADMIN, reply_markup=kb, parse_mode='HTML', caption=caption)
    await message.delete()
    await message.bot.edit_message_text(text=texts.get('pay_process'), **args)


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
    await callback.bot.send_message(chat_id=user, text=texts.get(f'pay_{action}'), reply_markup=kb)
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
    delta = "'+1 minute'" if config.test_mode else "'+' || period || ' days'"
    query = f'''
        update payments set start_date = ?, end_date = datetime(?, {delta}), status = 'active'
        where user_id = ? and start_date is NULL and status = "accepted"
        returning end_date
    '''
    start_date = f'{datetime.now():%F %T}'
    result = db.execute_query(query, start_date, start_date, user.id)
    user_name = user.username or user.first_name
    if not result:
        await remove_user(user.id, user_name)
        return
    end_date = result[0]['end_date']
    if end_date:
        schedule_jobs(user.id, user_name, end_date)
    text = texts.get('user_join').format(get_user_link(user))
    await event.bot.send_message(chat_id=ADMIN, text=text, parse_mode='HTML')
