import requests
import pandas as pd
from datetime import datetime, date
from typing import List, Dict, Optional
from models.bond import Bond
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MoexAPI:
    BASE_URL = "https://iss.moex.com/iss"
    BONDS_MARKET_URL = f"{BASE_URL}/engines/stock/markets/bonds/securities.json"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "BondAnalyzer/1.0 (Python)"
        })

    def fetch_bonds_list(self, batch_size: int = 100) -> List[Dict]:
        logger.info("Запрос ВСЕХ облигаций с MOEX (пагинация)...")
        all_securities = []
        all_marketdata = []

        start = 0
        while True:
            params = {
                "start": start,
                "limit": batch_size,
                "iss.only": "securities,marketdata",
                "securities.columns": (
                    "SECID,ISIN,NAME,COUPONPERCENT,COUPONPERIOD,"
                    "NEXTCOUPON,MATDATE,FACEVALUE,SECTYPE"
                ),
                "marketdata.columns": "SECID,LAST,MARKETPRICE,YIELDTOMATURITY,ACCRUEDINT"
            }

            try:
                response = self.session.get(self.BONDS_MARKET_URL, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()

                securities = self._parse_iss_section(data, "securities")
                marketdata = self._parse_iss_section(data, "marketdata")

                if not securities:
                    logger.info(f"Получено {len(all_securities)} облигаций. Больше данных нет.")
                    break

                all_securities.extend(securities)
                all_marketdata.extend(marketdata)
                logger.debug(f"Загружено {len(all_securities)} облигаций (start={start})")
                start += batch_size

                if len(securities) < batch_size:
                    break

            except Exception as e:
                logger.error(f"Ошибка на странице start={start}: {e}")
                break

        if not all_securities or not all_marketdata:
            logger.warning("Пустой ответ от MOEX API")
            return []

        df_securities = pd.DataFrame(all_securities)
        df_marketdata = pd.DataFrame(all_marketdata)
        df = pd.merge(df_securities, df_marketdata, on="SECID", how="inner")
        bonds_data = df.to_dict(orient="records")
        logger.info(f"Итого получено {len(bonds_data)} облигаций после объединения")
        return bonds_data

    def _parse_iss_section(self, json_data: dict, section_name: str) -> List[Dict]:
        try:
            columns = json_data[section_name]["columns"]
            data = json_data[section_name]["data"]
            return [dict(zip(columns, row)) for row in data]
        except (KeyError, TypeError):
            return []

    def parse_bond(self, raw_data: dict) -> Optional[Bond]:
        try:
            secid = raw_data.get("SECID")
            isin = raw_data.get("ISIN")
            name = raw_data.get("NAME", "Unknown")
            coupon_rate = float(raw_data.get("COUPONPERCENT", 0) or 0)
            coupon_period = int(raw_data.get("COUPONPERIOD", 182) or 182)
            matdate_str = raw_data.get("MATDATE")
            face_value = float(raw_data.get("FACEVALUE", 1000) or 1000)

            price = raw_data.get("LAST") or raw_data.get("MARKETPRICE")
            if price is None:
                return None
            price = float(price)

            accrued_interest = float(raw_data.get("ACCRUEDINT", 0) or 0)

            next_coupon_str = raw_data.get("NEXTCOUPON")
            coupon_next_date = self._parse_date(next_coupon_str) if next_coupon_str else date.today()

            maturity_date = self._parse_date(matdate_str)
            if not maturity_date or maturity_date <= date.today():
                return None

            sectype = raw_data.get("SECTYPE", "")
            if "OFZ" in sectype or "GOS" in sectype or "TRES" in name.upper():
                sector = "government"
            elif "CORP" in sectype or "CORP" in name.upper():
                sector = "corporate"
            else:
                sector = "other"

            ytm_raw = raw_data.get("YIELDTOMATURITY")
            ytm = float(ytm_raw) if ytm_raw is not None and ytm_raw != '' else None

            bond = Bond(
                isin=isin,
                secid=secid,
                name=name,
                coupon_rate=coupon_rate,
                coupon_period=coupon_period,
                coupon_next_date=coupon_next_date,
                maturity_date=maturity_date,
                price=price,
                yield_to_maturity=ytm,
                face_value=face_value,
                accrued_interest=accrued_interest,
                sector=sector
            )

            if bond.yield_to_maturity is None:
                bond.yield_to_maturity = bond.calculate_ytm()

            return bond

        except (ValueError, TypeError, KeyError) as e:
            logger.debug(f"Ошибка парсинга облигации {raw_data.get('SECID')}: {e}")
            return None

    def _parse_date(self, date_str: str) -> Optional[date]:
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return None

    def get_all_bonds(self) -> List[Bond]:
        raw_bonds = self.fetch_bonds_list(batch_size=100)
        bonds = []
        for raw in raw_bonds:
            bond = self.parse_bond(raw)
            if bond:
                bonds.append(bond)
        logger.info(f"Успешно обработано {len(bonds)} облигаций")
        return bonds