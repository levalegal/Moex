from datetime import datetime, time
import pytz

MOSCOW_TZ = pytz.timezone('Europe/Moscow')

def is_trading_now() -> bool:
    now = datetime.now(MOSCOW_TZ)
    current_time = now.time()
    current_weekday = now.weekday()
    if current_weekday >= 5:
        return False
    if time(10, 0) <= current_time <= time(18, 40):
        return True
    if time(19, 0) <= current_time <= time(23, 50):
        return True
    return False

def get_current_trading_status() -> str:
    if is_trading_now():
        return "🟢 Торги идут"
    else:
        return "🔴 Торги не идут"