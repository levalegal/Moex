# api/moex_api.py

import requests
import pandas as pd
from typing import List, Dict, Optional
from config import MOEX_BONDS_MARKET_URL, MOEX_BONDS_PARAMS, get_coupon_url


class MoexAPI:
    """
    Класс для работы с API Московской биржи (MOEX ISS).
    """

    @staticmethod
    def _fetch_json(url: str, params: Optional[Dict] = None) -> dict:
        """
        Выполняет GET-запрос и возвращает JSON.
        """
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise ConnectionError(f"Ошибка при запросе к MOEX API: {e}")

    @classmethod
    def fetch_bonds_list(cls) -> pd.DataFrame:
        """
        Получает список облигаций с рынка TQCB.
        Возвращает pandas DataFrame с объединёнными данными securities + marketdata.
        """
        data = cls._fetch_json(MOEX_BONDS_MARKET_URL, MOEX_BONDS_PARAMS)

        # Извлекаем данные из структуры ISS
        securities_data = data.get('securities', {}).get('data', [])
        securities_columns = data.get('securities', {}).get('columns', [])

        marketdata_data = data.get('marketdata', {}).get('data', [])
        marketdata_columns = data.get('marketdata', {}).get('columns', [])

        # Преобразуем в DataFrame
        df_securities = pd.DataFrame(securities_data, columns=securities_columns)
        df_marketdata = pd.DataFrame(marketdata_data, columns=marketdata_columns)

        # Объединяем по SECID
        df = pd.merge(df_securities, df_marketdata, on='SECID', how='inner')

        return df

    @classmethod
    def fetch_coupon_periods(cls, isin: str) -> List[Dict]:
        """
        Получает список купонных периодов для облигации по ISIN.
        Возвращает список словарей с датами и размерами купонов.
        """
        url = get_coupon_url(isin)
        try:
            data = cls._fetch_json(url)
        except ConnectionError:
            # Некоторые облигации (например, ОФЗ) могут не иметь купонов в этом эндпоинте
            return []

        coupons_data = data.get('couponperiods', {}).get('data', [])
        coupons_columns = data.get('couponperiods', {}).get('columns', [])

        coupons = [dict(zip(coupons_columns, row)) for row in coupons_data]
        return coupons