# models/bond.py

from datetime import datetime
from typing import List, Optional, Dict


class Bond:
    """
    Модель облигации.
    Хранит все необходимые атрибуты и предоставляет методы для анализа.
    """

    def __init__(
        self,
        secid: str,
        isin: str,
        name: str,
        price: float,                     # Цена в рублях (MARKETPRICE или LAST)
        nominal: float,                   # Номинал в рублях (FACEVALUE)
        coupon_rate: Optional[float],     # Годовая купонная ставка в % (может быть None)
        maturity_date: str,               # Дата погашения в формате 'YYYY-MM-DD'
        accrued_interest: float,          # НКД (в рублях)
        volume_rub: float,                # Объём торгов за день в рублях
        coupon_periods: List[Dict],       # Список купонных периодов от MOEX
        boardid: str = "TQCB"
    ):
        self.secid = secid
        self.isin = isin
        self.name = name
        self.price = price
        self.nominal = nominal
        self.coupon_rate = coupon_rate
        self.maturity_date = datetime.strptime(maturity_date, "%Y-%m-%d").date()
        self.accrued_interest = accrued_interest
        self.volume_rub = volume_rub
        self.coupon_periods = coupon_periods
        self.boardid = boardid

        # Поля, которые будут заполнены позже (например, после расчёта YTM)
        self.yield_to_maturity: Optional[float] = None  # в долях (не в %)
        self.years_to_maturity: Optional[float] = None

    @property
    def clean_price(self) -> float:
        """Чистая цена (без НКД)"""
        return self.price - self.accrued_interest

    @property
    def is_zero_coupon(self) -> bool:
        """Является ли облигация бескупонной"""
        if self.coupon_rate is None:
            return len(self.coupon_periods) == 0
        return self.coupon_rate == 0.0

    @property
    def next_coupon_date(self) -> Optional[datetime.date]:
        """Дата следующего купона (если есть)"""
        if not self.coupon_periods:
            return None
        # Купоны отсортированы по дате? Предположим, что да.
        today = datetime.today().date()
        for cp in self.coupon_periods:
            try:
                date = datetime.strptime(cp['coupondate'], "%Y-%m-%d").date()
                if date > today:
                    return date
            except (KeyError, ValueError):
                continue
        return None

    def __repr__(self):
        return (
            f"Bond(ISIN={self.isin}, name='{self.name}', "
            f"price={self.price:.2f}, YTM={self.yield_to_maturity*100:.2f}% if calculated)"
        )

    def to_dict(self) -> dict:
        """Преобразует объект в словарь для сериализации"""
        return {
            "secid": self.secid,
            "isin": self.isin,
            "name": self.name,
            "price": self.price,
            "clean_price": self.clean_price,
            "nominal": self.nominal,
            "coupon_rate": self.coupon_rate,
            "maturity_date": self.maturity_date.isoformat(),
            "accrued_interest": self.accrued_interest,
            "volume_rub": self.volume_rub,
            "yield_to_maturity_percent": round(self.yield_to_maturity * 100, 2) if self.yield_to_maturity else None,
            "years_to_maturity": round(self.years_to_maturity, 2) if self.years_to_maturity else None,
            "is_zero_coupon": self.is_zero_coupon
        }