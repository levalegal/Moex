# analyzers/bond_analyzer.py

from typing import List, Optional
from models.bond import Bond
from utils.helpers import calculate_ytm, is_valid_bond, years_fraction
from datetime import datetime
from config import ANALYSIS_SETTINGS


class BondAnalyzer:
    """
    Анализатор облигаций.
    Отвечает за фильтрацию, расчёт YTM и выбор наиболее выгодных облигаций.
    """

    def __init__(self, settings: dict = None):
        self.settings = settings or ANALYSIS_SETTINGS

    def analyze(self, bonds: List[Bond]) -> List[Bond]:
        """
        Анализирует список облигаций:
        1. Фильтрует по критериям (ликвидность, срок, тип и т.д.)
        2. Рассчитывает YTM для каждой
        3. Сортирует по убыванию YTM
        4. Возвращает топ-N облигаций
        """
        valid_bonds = []

        for bond in bonds:
            # 1. Проверка валидности
            if not is_valid_bond(bond, self.settings):
                continue

            # 2. Расчёт YTM
            ytm = calculate_ytm(bond)
            if ytm is None or ytm < self.settings.get("min_yield", 0):
                continue

            # Сохраняем результат
            bond.yield_to_maturity = ytm
            bond.years_to_maturity = years_fraction(datetime.today().date(), bond.maturity_date)
            valid_bonds.append(bond)

        # 3. Сортировка по YTM (по убыванию)
        valid_bonds.sort(key=lambda b: b.yield_to_maturity, reverse=True)

        # 4. Возвращаем топ-N
        top_n = self.settings.get("top_n", 1)
        return valid_bonds[:top_n]