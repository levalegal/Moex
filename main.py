# main.py

import json
import sys
import pandas as pd  # Переносим импорт наверх!
from api.moex_api import MoexAPI
from models.bond import Bond
from analyzers.bond_analyzer import BondAnalyzer
from config import ANALYSIS_SETTINGS


def safe_float(value, default=None):
    """Безопасное преобразование в float."""
    if value is None or (isinstance(value, str) and value.strip() in ('', '-', 'None')):
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def create_bond_objects(df) -> list:
    bonds = []
    skipped = 0
    for idx, row in df.iterrows():
        try:
            secid = row.get('SECID')
            isin = row.get('ISIN')
            name = row.get('NAME')
            faceunit = row.get('FACEUNIT', 'SUR')
            maturity_date = row.get('MATDATE')

            # Пропускаем, если критически важные поля отсутствуют
            if not secid or not isin or not name or not maturity_date:
                skipped += 1
                continue

            # Пропускаем некорректные даты погашения
            if maturity_date == "0000-00-00" or not maturity_date.replace('-', '').isdigit():
                skipped += 1
                continue

            # Определяем номинал в рублях
            facevalue_raw = safe_float(row.get('FACEVALUE'))
            if facevalue_raw is None:
                skipped += 1
                continue

            # Если FACEUNIT = 'PCNT', то номинал = 1000 (стандарт для облигаций РФ)
            # Но на самом деле: если указано в %, то реальный номинал — 1000 руб.
            if faceunit == 'PCNT':
                nominal = 1000.0
            else:
                nominal = facevalue_raw

            # Цена
            price = safe_float(row.get('MARKETPRICE'))
            if price is None:
                price = safe_float(row.get('LAST'))
            if price is None or price <= 0:
                skipped += 1
                continue

            # НКД
            accrued_interest = safe_float(row.get('ACCRUEDINT'), 0.0)

            # Объём
            volume_rub = safe_float(row.get('VOLRUR'), 0.0)
            if volume_rub == 0:
                volume_rub = safe_float(row.get('VALTODAY'), 0.0)

            # Купонная ставка
            coupon_rate = safe_float(row.get('COUPON_PERCENT'))

            # Получаем купоны
            coupon_periods = MoexAPI.fetch_coupon_periods(isin)

            bond = Bond(
                secid=secid,
                isin=isin,
                name=str(name),
                price=price,
                nominal=nominal,
                coupon_rate=coupon_rate,
                maturity_date=maturity_date,
                accrued_interest=accrued_interest,
                volume_rub=volume_rub,
                coupon_periods=coupon_periods
            )
            bonds.append(bond)

        except Exception as e:
            skipped += 1
            # Раскомментируйте для отладки:
            # print(f"Ошибка при обработке строки {idx}: {e}")
            continue

    print(f"   → Пропущено: {skipped} строк из-за ошибок или некорректных данных.")
    return bonds


def main():
    print("🔍 Получение данных с Московской биржи...")
    try:
        df = MoexAPI.fetch_bonds_list()
        print(f"📥 Получено {len(df)} облигаций.")
    except Exception as e:
        print(f"❌ Ошибка при получении данных: {e}", file=sys.stderr)
        sys.exit(1)

    print("📦 Преобразование в объекты Bond...")
    bonds = create_bond_objects(df)
    print(f"✅ Создано {len(bonds)} валидных объектов облигаций.")

    if not bonds:
        print("⚠️ Нет облигаций для анализа. Попробуйте:")
        print("   - Увеличить лимит (убрать limit в config)")
        print("   - Временно отключить фильтры (min_volume_rub=0 и т.д.)")
        return

    print("📊 Анализ облигаций...")
    analyzer = BondAnalyzer(settings=ANALYSIS_SETTINGS)
    best_bonds = analyzer.analyze(bonds)

    if not best_bonds:
        print("⚠️ Не найдено облигаций, удовлетворяющих критериям.")
        print("   Совет: временно установите 'min_yield': -1 и 'min_volume_rub': 0 в config.py")
        return

    print("\n" + "="*80)
    print("🏆 САМАЯ ВЫГОДНАЯ ОБЛИГАЦИЯ:")
    print("="*80)

    best = best_bonds[0]
    print(f"Название:       {best.name}")
    print(f"ISIN:           {best.isin}")
    print(f"Цена (грязная): {best.price:.2f} ₽")
    print(f"Чистая цена:    {best.clean_price:.2f} ₽")
    print(f"НКД:            {best.accrued_interest:.2f} ₽")
    print(f"Номинал:        {best.nominal:.2f} ₽")
    print(f"Купон (% год):  {best.coupon_rate if best.coupon_rate else '—'}")
    print(f"Дата погашения: {best.maturity_date}")
    print(f"Срок до погашения: {best.years_to_maturity:.2f} лет")
    print(f"Доходность (YTM): {best.yield_to_maturity * 100:.2f}% годовых")
    print(f"Объём торгов:   {best.volume_rub:,.0f} ₽")
    print(f"SECID:          {best.secid}")

    print("\n📄 JSON-результат:")
    print(json.dumps(best.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()