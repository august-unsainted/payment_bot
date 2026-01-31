from datetime import datetime, timedelta
from pathlib import Path

from aiogram.types import User
from apscheduler.jobstores.base import JobLookupError
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot_config import config
from utils.user_actions import notify_user, remove_user

jobstores = {'default': SQLAlchemyJobStore(url=f'sqlite:///{Path().cwd() / 'data/bot.db'}')}
scheduler = AsyncIOScheduler(timezone='Asia/Irkutsk', jobstores=jobstores)


def start_scheduler():
    scheduler.start()


def schedule_jobs(user: User, date: str):
    end_date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
    delta = timedelta(seconds=30) if config.test_mode else timedelta(days=3)
    scheduler.add_job(id=f'{user.id}_notify', trigger='date', run_date=end_date - delta,
                      func=notify_user, args=[user.id], replace_existing=True)
    scheduler.add_job(id=str(user.id), trigger='date', run_date=end_date,
                      func=remove_user, args=[user.id, user.first_name], replace_existing=True)


def remove_job(job_id: int | str):
    try:
        scheduler.remove_job(job_id)
    except JobLookupError:
        pass
