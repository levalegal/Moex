# Moex Data Fetcher

Асинхронный Python-инструмент для получения и обработки исторических данных с Московской Биржи (MOEX).

## 📋 Описание

Этот проект предоставляет набор асинхронных функций и классов для эффективного сбора данных о торгах (свечи, стаканы, тики) по ценным бумагам с официального API MOEX ISS. Использование асинхронного подхода (`aiohttp`) позволяет значительно ускорить загрузку больших объемов данных.

## ✨ Особенности


*   **Асинхронные запросы:** Быстрая параллельная загрузка данных для разных инструментов или периодов.
*   **Гибкость:** Поддержка различных временных интервалов (свечи) и типов данных.
*   **Пакетная обработка:** Удобные функции для получения данных за длительные периоды.
*   **Преобразование данных:** Автоматическое приведение данных к типам `pandas` (DateTime, numeric).
*   **Простота использования:** Чистый и понятный API.

## 🛠 Технологии

*   Python 3.7+
*   [aiohttp](https://docs.aiohttp.org/) - Асинхронные HTTP-запросы
*   [pandas](https://pandas.pydata.org/) - Обработка и анализ данных
*   [asyncio](https://docs.python.org/3/library/asyncio.html) - Асинхронное программирование

## 📦 Установка

1.  Клонируйте репозиторий:
    ```bash
    git clone https://github.com/ETsETs777/Moex.git
    cd Moex
    ```

2.  Установите зависимости:
    ```bash
    pip install -r requirements.txt
    ```

    *Если файла `requirements.txt` нет, установите пакеты вручную:*
    ```bash
    pip install aiohttp pandas
    ```

## 🚀 Быстрый старт

Вот простой пример, как получить свечи (бары) для акции Сбербанка за последние 10 дней.

```python
import asyncio
from moex_data_fetcher import MoexFetcher

async def main():
    # Создаем экземпляр загрузчика
    fetcher = MoexFetcher()
    
    # Тикер Сбербанка
    ticker = 'SBER'
    
    # Получаем дневные свечи
    data = await fetcher.get_candles(
        security=ticker,
        interval='D',  # День
        count=10       # Последние 10 свечей
    )
    
    print(data.head())

# Запускаем асинхронную функцию
if __name__ == "__main__":
    asyncio.run(main())
📖 Документация
Основные методы
get_candles(security, interval, from_date=None, till_date=None, count=None)
Получает исторические свечи для указанного инструмента.

security (str): Тикер ценной бумаги (например, 'SBER', 'GAZP').

interval (str): Интервал свечей:

'1' - 1 минута

'10' - 10 минут

'60' - 1 час

'D' - 1 день

'W' - 1 неделя

'M' - 1 месяц

'
from_date (str): Начальная дата в формате 'YYYY-MM-DD'.

till_date (str): Конечная дата в формате 'YYYY-MM-DD'.

count (int): Количество последних свечей для получения.

Возвращает: pandas.DataFrame с колонками ['open', 'high', 'low', 'close', 'volume', 'begin', 'end'].

get_securities(board_group=None)
Получает список всех торгуемых ценных бумаг.

board_group (int): Фильтр по группе режима торгов (опционально).

Возвращает: pandas.DataFrame с информацией о бумагах.

Примеры использования
Пример 1: Получение данных за конкретный период

python
data = await fetcher.get_candles(
    security='VTBR',
    interval='D',
    from_date='2024-01-01',
    till_date='2024-03-01'
)
Пример 2: Получение часовых данных для индекса МосБиржи
рустор

python
data = await fetcher.get_candles(
    security='IMOEX',
    interval='60',
    count=100
)
Пример 3: Поиск всех акций

python
securities_df = await fetcher.get_securities()
stocks = securities_df[securities_df['type'] == 'common_share']
print(stocks[['secid', 'name']].head())
