from datetime import timedelta
from pathlib import Path

from aiogram import Bot
from aiogram.types import User
from apscheduler.jobstores.base import JobLookupError
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot_config import config
from config import ADMIN
from utils.database import update_payment
from utils.user_actions import notify_user, remove_user, get_date, format_event_message

jobstores = {'default': SQLAlchemyJobStore(url=f'sqlite:///{Path().cwd() / 'data/bot.db'}')}
scheduler = AsyncIOScheduler(timezone='Asia/Irkutsk', jobstores=jobstores)


def start_scheduler():
    scheduler.start()


def schedule_jobs(user_id: int, name: str, date: str, channel: int):
    end_date = get_date(date)
    delta = timedelta(seconds=110) if config.test_mode else timedelta(days=3)
    job_id = f'{user_id}_{channel}'
    args = {'trigger':            'date',
            'misfire_grace_time': 60 * 60 * 72,
            'replace_existing':   True
            }
    scheduler.add_job(id=f'{job_id}_notify', run_date=end_date - delta, func=notify_user, args=[user_id, channel], **args)
    scheduler.add_job(id=job_id, run_date=end_date, func=remove_user, args=[user_id, name, channel], **args)


def remove_job(job_id: int | str):
    for job in (job_id, f'{job_id}_notify'):
        try:
            scheduler.remove_job(job)
        except JobLookupError:
            pass


async def activate_sub(user: User, action: str, chat: int, bot: Bot):
    user_id, name = user.id, user.first_name
    result = update_payment(user_id, chat)
    if not result:
        await remove_user(user_id, name, chat)
        return
    remove_job(user_id)
    end_date = result[0]['end_date']
    if end_date:
        schedule_jobs(user_id, name, end_date, chat)
    text = format_event_message(action, chat, user)
    await bot.send_message(chat_id=ADMIN, text=text, parse_mode='HTML')
