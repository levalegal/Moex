# utils/helpers.py

import math
from datetime import datetime, date
from typing import List, Dict, Optional
from models.bond import Bond


def days_between(start_date: date, end_date: date) -> int:
    """Возвращает количество дней между двумя датами."""
    return (end_date - start_date).days


def years_fraction(start_date: date, end_date: date) -> float:
    """
    Возвращает дробное количество лет между датами.
    Используется ACT/ACT (фактическое количество дней / 365.25).
    """
    days = days_between(start_date, end_date)
    return days / 365.25


def get_coupon_schedule(bond: Bond) -> List[Dict[str, float]]:
    """
    Возвращает график купонных выплат в виде списка:
    [{'time': t1, 'amount': c1}, {'time': t2, 'amount': c2}, ..., {'time': tN, 'amount': cN + nominal}]
    где t — время в годах от сегодняшнего дня.
    """
    today = datetime.today().date()
    schedule = []

    # Если есть купонные периоды от MOEX — используем их
    if bond.coupon_periods:
        for cp in bond.coupon_periods:
            try:
                coupon_date_str = cp['coupondate']
                coupon_value = float(cp['value'])  # в рублях
                coupon_date = datetime.strptime(coupon_date_str, "%Y-%m-%d").date()
                if coupon_date <= today:
                    continue  # пропускаем прошедшие купоны
                t = years_fraction(today, coupon_date)
                schedule.append({"time": t, "amount": coupon_value})
            except (KeyError, ValueError, TypeError):
                continue

    # Если купонов нет (или не удалось распарсить), пытаемся использовать купонную ставку
    if not schedule and bond.coupon_rate and not bond.is_zero_coupon:
        # Простая аппроксимация: раз в год или раз в полгода
        freq = 2 if bond.coupon_rate > 0 else 1  # по умолчанию — полугодовые купоны
        years_to_maturity = years_fraction(today, bond.maturity_date)
        periods = max(1, int(years_to_maturity * freq))
        coupon_amount = (bond.coupon_rate / 100) * bond.nominal / freq
        for i in range(1, periods + 1):
            t = i / freq
            if t > years_to_maturity:
                break
            schedule.append({"time": t, "amount": coupon_amount})

    # Добавляем погашение номинала в конец
    if schedule:
        last_time = schedule[-1]["time"]
        maturity_time = years_fraction(today, bond.maturity_date)
        if abs(maturity_time - last_time) > 0.01:  # если погашение не совпадает с последним купоном
            schedule.append({"time": maturity_time, "amount": bond.nominal})
        else:
            # Добавляем номинал к последнему купону
            schedule[-1]["amount"] += bond.nominal
    else:
        # Бескупонная облигация: только погашение
        maturity_time = years_fraction(today, bond.maturity_date)
        schedule.append({"time": maturity_time, "amount": bond.nominal})

    return schedule


def calculate_ytm(bond: Bond, tolerance: float = 1e-6, max_iterations: int = 1000) -> Optional[float]:
    """
    Рассчитывает доходность к погашению (YTM) с использованием метода бинарного поиска.
    Возвращает YTM в долях (не в процентах), например 0.085 = 8.5%.
    """
    clean_price = bond.clean_price
    if clean_price <= 0:
        return None

    schedule = get_coupon_schedule(bond)
    if not schedule:
        return None

    # Определим границы поиска: от -50% до +200% годовых (в долях: -0.5 до 2.0)
    low = -0.5
    high = 2.0

    def npv(rate: float) -> float:
        """Чистая приведённая стоимость при заданной ставке."""
        total = 0.0
        for item in schedule:
            t = item["time"]
            c = item["amount"]
            if rate <= -1:
                return float('inf')
            total += c / ((1 + rate) ** t)
        return total

    # Проверим граничные значения
    npv_low = npv(low)
    npv_high = npv(high)

    # Если цена вне диапазона — выходим
    if clean_price > npv_low or clean_price < npv_high:
        # Попробуем расширить диапазон или вернуть None
        return None

    # Бинарный поиск
    for _ in range(max_iterations):
        mid = (low + high) / 2
        npv_mid = npv(mid)

        if abs(npv_mid - clean_price) < tolerance:
            return mid

        if npv_mid > clean_price:
            low = mid
        else:
            high = mid

    # Если не сошлось — возвращаем последнее приближение
    return (low + high) / 2


def is_valid_bond(bond: Bond, settings: dict) -> bool:
    """
    Проверяет, подходит ли облигация под критерии фильтрации.
    """
    today = datetime.today().date()

    # Проверка срока до погашения
    years_to_maturity = years_fraction(today, bond.maturity_date)
    if years_to_maturity <= 0:
        return False
    if years_to_maturity > settings.get("max_maturity_years", 30):
        return False

    # Исключить бескупонные, если нужно
    if settings.get("exclude_zero_coupon", False) and bond.is_zero_coupon:
        return False

    # Минимальный объём торгов
    if bond.volume_rub < settings.get("min_volume_rub", 0):
        return False

    return True