from typing import List, Optional
from datetime import date
from models.bond import Bond
import logging

logger = logging.getLogger(__name__)


class BondCalculator:
    def __init__(
        self,
        min_years_to_maturity: float = 0.5,
        max_years_to_maturity: float = 30.0,
        prefer_government: bool = True,
        min_ytm_threshold: float = 0.0
    ):
        self.min_years_to_maturity = min_years_to_maturity
        self.max_years_to_maturity = max_years_to_maturity
        self.prefer_government = prefer_government
        self.min_ytm_threshold = min_ytm_threshold

    def filter_bonds(self, bonds: List[Bond]) -> List[Bond]:
        filtered = []
        for bond in bonds:
            ytm = bond.years_to_maturity
            if not (self.min_years_to_maturity <= ytm <= self.max_years_to_maturity):
                continue
            if bond.yield_to_maturity is None or bond.yield_to_maturity < self.min_ytm_threshold:
                continue
            if bond.price <= 0 or bond.price > 200:
                continue
            filtered.append(bond)
        logger.info(f"После фильтрации осталось {len(filtered)} облигаций")
        return filtered

    def score_bond(self, bond: Bond) -> float:
        score = bond.yield_to_maturity or 0.0
        if self.prefer_government and bond.sector == "government":
            score += 0.5
        return score

    def find_best_bond(self, bonds: List[Bond]) -> Optional[Bond]:
        filtered = self.filter_bonds(bonds)
        if not filtered:
            logger.warning("Нет облигаций, прошедших фильтрацию")
            return None
        best = max(filtered, key=self.score_bond)
        logger.info(f"Лучшая облигация: {best.secid} (YTM={best.yield_to_maturity:.2f}%)")
        return best

    def get_top_bonds(self, bonds: List[Bond], top_n: int = 10) -> List[Bond]:
        filtered = self.filter_bonds(bonds)
        scored = [(self.score_bond(b), b) for b in filtered]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [b for _, b in scored[:top_n]]