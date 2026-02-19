from datetime import datetime
from bot_config import db, config


def get_active_sub(user_id: int, channel: int):
    query = 'select * from payments where user_id = ? and channel = ? and status = "active"'
    subs = db.execute_query(query, user_id, channel)
    return subs[0] if subs else None


def insert_payment(cost: int, period: int, user_id: int, channel: int) -> int:
    active_payment = get_active_sub(user_id, channel)
    if active_payment:
        period += active_payment['period']
        update_status('inactive', active_payment['id'])
    query = 'insert into payments (user_id, channel, sum, period) values (?, ?, ?, ?)'
    return db.execute_query(query, user_id, channel, cost, period)


def update_payment(user_id: int, channel: int):
    delta = "'+2 minute'" if config.test_mode else "'+' || period || ' days'"
    query = f'''
        update payments
        set start_date = ?,
            end_date =
            case
                when period is null then null
                else datetime(?, {delta})
            end,
            status = 'active'
        where user_id = ? and channel = ? and start_date is null and status = "accepted"
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

