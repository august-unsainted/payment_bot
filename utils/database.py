from datetime import datetime
from bot_config import db, config, prices
from utils.date_funcs import get_date


def get_active_sub(user_id: int, channel: int):
    query = 'select * from payments where user_id = ? and channel = ? and status = "active"'
    subs = db.execute_query(query, user_id, channel)
    return subs[0] if subs else None


def insert_payment(period: str, user_id: int, channel: int) -> int:
    price = prices[period]
    cost, days = price['cost'], price['days']
    active_payment = get_active_sub(user_id, channel)
    end_date = None
    if active_payment:
        end_date = active_payment['end_date']
        update_status('inactive', active_payment['id'])
    query = 'insert into payments (user_id, channel, period, sum, days, end_date) values (?, ?, ?, ?, ?, ?)'
    return db.execute_query(query, user_id, channel, period, cost, days, end_date)


def update_payment(user_id: int, channel: int):
    delta = "'+1 minute'" if config.test_mode else "'+' || days || ' days'"
    query = f'''
        update payments
        set start_date = ?,
            end_date =
            case
                when days is null then null
                when end_date is null then datetime(?, {delta})
                else datetime(end_date, {delta})
            end,
            status = 'active'
        where user_id = ? and channel = ? and start_date is null and status = "accepted"
        returning end_date
    '''
    start_date = f'{datetime.now():%F %T}'
    return db.execute_query(query, start_date, start_date, user_id, channel)


def set_inactive(user_id: int, channel: int):
    query = f'update payments set status = "inactive" where user_id = ? and channel = ? and status = "active" returning id'
    return db.execute_query(query, user_id, channel)


def update_status(status: str, pay_id: str):
    db.execute_query('update payments set status = ? where id = ?', status, pay_id)


def get_payment(pay_id: str):
    return db.execute_query('select * from payments where id = ?', pay_id)[0]
