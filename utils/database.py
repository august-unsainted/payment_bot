from datetime import datetime
from bot_config import db, config


def insert_payment(cost: int, period: int, user_id: int, channel: int) -> int:
    query = 'select id, period from payments where user_id = ? and channel = ? and status = "active"'
    prev_payments = db.execute_query(query, user_id, channel)
    if prev_payments:
        prev_pay = prev_payments[0]
        period += prev_pay['period']
        update_status('inactive', prev_pay['id'])
    query = 'insert into payments (user_id, channel, sum, period) values (?, ?, ?, ?)'
    return db.execute_query(query, user_id, channel, cost, period)


def activate_sub(user_id: int, channel: int):
    delta = "'+1 minute'" if config.test_mode else "'+' || period || ' days'"
    query = f'''
        update payments set start_date = ?, end_date = datetime(?, {delta}), status = 'active'
        where user_id = ? and channel = ? and start_date is NULL and status = "accepted"
        returning end_date
    '''
    start_date = f'{datetime.now():%F %T}'
    return db.execute_query(query, start_date, start_date, user_id, channel)


def set_inactive(value: int, channel: int):
    query = f'update payments set status = "inactive" where user_id = ? and channel = ? and status = "active"'
    db.execute_query(query, value, channel)


def update_status(status: str, pay_id: str):
    db.execute_query('update payments set status = ? where id = ?', status, pay_id)


def get_payment(pay_id: str):
    return db.execute_query('select * from payments where id = ?', pay_id)[0]

