from datetime import datetime, date
from typing import Optional
import numpy as np


class Bond:
    def __init__(
        self,
        isin: str,
        secid: str,
        name: str,
        coupon_rate: float,
        coupon_period: int,
        coupon_next_date: date,
        maturity_date: date,
        price: float,
        yield_to_maturity: Optional[float] = None,
        face_value: float = 1000.0,
        accrued_interest: float = 0.0,
        sector: str = "unknown"
    ):
        self.isin = isin
        self.secid = secid
        self.name = name
        self.coupon_rate = coupon_rate
        self.coupon_period = coupon_period
        self.coupon_next_date = coupon_next_date
        self.maturity_date = maturity_date
        self.price = price
        self.yield_to_maturity = yield_to_maturity
        self.face_value = face_value
        self.accrued_interest = accrued_interest
        self.sector = sector

    @property
    def current_yield(self) -> float:
        annual_coupon = self.face_value * (self.coupon_rate / 100)
        price_rub = self.price / 100 * self.face_value
        if price_rub == 0:
            return 0.0
        return (annual_coupon / price_rub) * 100

    @property
    def years_to_maturity(self) -> float:
        if self.maturity_date <= date.today():
            return 0.0
        delta = self.maturity_date - date.today()
        return delta.days / 365.25

    def calculate_ytm(self, max_iter: int = 100, tolerance: float = 1e-6) -> float:
        if self.years_to_maturity <= 0:
            return 0.0

        n_coupons = max(1, int(self.years_to_maturity * 365 / self.coupon_period))
        coupon_payment = (self.coupon_rate / 100 * self.face_value) * (self.coupon_period / 365)
        price_clean = (self.price / 100) * self.face_value

        def price_diff(y):
            y = y / 100
            pv_coupons = sum(
                coupon_payment / (1 + y * self.coupon_period / 365) ** i
                for i in range(1, n_coupons + 1)
            )
            pv_face = self.face_value / (1 + y * self.coupon_period / 365) ** n_coupons
            return pv_coupons + pv_face - price_clean

        low, high = 0.0, 100.0
        for _ in range(max_iter):
            mid = (low + high) / 2
            diff = price_diff(mid)
            if abs(diff) < tolerance:
                return mid
            if diff > 0:
                low = mid
            else:
                high = mid
        return mid

    def __repr__(self):
        return f"<Bond {self.secid} | YTM: {self.yield_to_maturity or 'N/A'}% | Price: {self.price}%>"

    def to_dict(self) -> dict:
        return {
            "ISIN": self.isin,
            "SECID": self.secid,
            "Name": self.name,
            "Coupon, %": round(self.coupon_rate, 2),
            "Price, %": round(self.price, 2),
            "YTM, %": round(self.yield_to_maturity, 2) if self.yield_to_maturity else None,
            "Current Yield, %": round(self.current_yield, 2),
            "Maturity": self.maturity_date.isoformat(),
            "Years to Maturity": round(self.years_to_maturity, 2),
            "Sector": self.sector
        }