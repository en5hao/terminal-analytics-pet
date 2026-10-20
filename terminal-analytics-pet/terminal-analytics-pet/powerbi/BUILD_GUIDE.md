# Сборка дашборда Power BI (`terminal_dashboard.pbix`)

Файл `.pbix` — бинарный формат Power BI Desktop, поэтому в репозитории лежит инструкция и меры (`measures.dax`).
Соберите отчёт по шагам и сохраните как `powerbi/terminal_dashboard.pbix`.

## 1. Источники
- **PostgreSQL** (`terminal_analytics`): таблицы `devices`, `transactions`, `maintenance` (схема — `sql/schema.sql`, загрузка — `sql/load.sql`).
- **CSV** `data/clean/device_consistency.csv` — таблица `device_consistency` (в БД её нет, она получена в Power Query).
- Типы: все `*_time`/`last_online` — «Дата/время», `cash_level`, `amount` — «Десятичное число».

## 2. Модель данных
| Связь | Тип | Фильтр |
|---|---|---|
| `devices[device_id]` → `transactions[device_id]` | 1 : * | одно направление |
| `devices[device_id]` → `maintenance[device_id]` | 1 : * | одно направление |
| `devices[device_id]` → `device_consistency[device_id]` | 1 : 1 | в обе стороны |

Связь 1 : 1 с `device_consistency` нужна, чтобы срезы `model` и `location` работали и на карточку *Anomaly Devices*.
Заявки на несуществующие устройства (M0005, M0023) остаются в `maintenance` без родителя — мера `MTTR Hours` их исключает.
Создайте таблицу `_measures` («Ввод данных») и добавьте меры из `measures.dax`; в `maintenance` — столбец `Ticket MTTR Hours`.

## 3. Страница Overview
- Срезы: `transactions[txn_time]` (диапазон), `devices[model]`, `devices[location]`.
- Карточки: `Success Rate`, `MTTR Hours`, `Anomaly Devices`, `Total Txns`.
- Линейный график: ось — `txn_time` (по дням), значение — `Total Txns`.
- Столбчатая: ось — `devices[device_id]`, значение — `Error Txns`, фильтр визуального «Первые N» = 5 по `Error Txns`.
- Таблица: `device_id`, `model`, `location`, `anomaly_reason` из `device_consistency`; фильтр визуального `anomaly_reason` ≠ «норма».
- Ожидаемые значения без срезов: 88,7 % / 5,62 / 6 / 655.

## 4. Страница Device Detail (drill-through)
1. Поле детализации: `devices[device_id]` (Визуализации → Добавить поля детализации).
2. Карточки `device_id`, `model`, `location`, `Success Rate`; таблица транзакций; столбчатая «коды ошибок» (`error_code`, значение — количество); таблица заявок (`fault_time`, `resolve_time`, `Ticket MTTR Hours`).
3. Скрыть страницу: ПКМ по вкладке → «Скрыть». Кнопка «Назад» появляется автоматически.
4. Проверка: Overview → ПКМ по устройству в таблице/столбчатой → «Детализация» → «Device Detail».

Скриншоты для `screenshots/powerbi/`: `overview.png`, `detail.png`, `drillthrough_menu.png`.
