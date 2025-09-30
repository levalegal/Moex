# config.py

# API endpoints
MOEX_API_BASE = "https://iss.moex.com/iss"

# Рынок облигаций на MOEX
MOEX_BONDS_MARKET_URL = f"{MOEX_API_BASE}/engines/stock/markets/bonds/securities.json"

# Параметры запроса для получения списка облигаций
MOEX_BONDS_PARAMS = {
    "iss.only": "securities,marketdata",
    "securities.columns": (
        "SECID,ISIN,NAME,ISSUE_SIZE,COUPON_PERCENT,COUPON_PERIOD,"
        "MATDATE,FACEVALUE,FACEUNIT,LISTLEVEL"
    ),
    "marketdata.columns": (
        "SECID,LAST,MARKETPRICE,BOARDID,VOLRUR,VALTODAY,ACCRUEDINT"
    ),
    # Фильтр: только корпоративные облигации на основном режиме торгов (TQCB)
    "boardid": "TQCB",
    # Опционально: можно добавить limit для тестирования
    # "limit": 100
}

# URL для получения купонных периодов по ISIN
def get_coupon_url(isin: str) -> str:
    return f"{MOEX_API_BASE}/statistics/engines/stock/markets/bonds/securities/{isin}/couponperiods.json"

# config.py (обновлённый блок ANALYSIS_SETTINGS)

ANALYSIS_SETTINGS = {
    "min_yield": -1.0,              # Разрешаем отрицательную доходность на время теста
    "max_maturity_years": 30,       # Увеличим до 30 лет
    "exclude_zero_coupon": False,   # Пока разрешаем бескупонные
    "min_volume_rub": 0,            # Отключаем фильтр по объёму
    "top_n": 1
}