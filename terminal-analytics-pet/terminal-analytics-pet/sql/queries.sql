-- 12 аналитических запросов, PostgreSQL. Период данных: 01–30.09.2026.
-- «Момент выгрузки» (snapshot) = 2026-09-30 23:59:59. Вместо now() используется он,
-- иначе результаты зависели бы от даты запуска и не воспроизводились.

-- 1. Коэффициент успешности по устройствам. Бизнес: рейтинг проблемных терминалов для приоритизации выездов.
SELECT d.device_id, d.model, d.location,
       COUNT(*)                                                        AS total_txns,
       COUNT(*) FILTER (WHERE t.status = 'success')                    AS success_txns,
       ROUND(100.0 * COUNT(*) FILTER (WHERE t.status = 'success') / COUNT(*), 1) AS success_rate_pct
FROM devices d JOIN transactions t USING (device_id)
GROUP BY d.device_id, d.model, d.location
ORDER BY success_rate_pct ASC, total_txns DESC
LIMIT 10;

-- 2. Устройства-«лжецы»: в мониторинге online, но транзакций > 3 дней (или нет вовсе). Бизнес: терминалы, которые числятся рабочими, но не приносят операций.
SELECT d.device_id, d.model, d.location, d.last_online,
       MAX(t.txn_time)  AS last_txn_time,
       COUNT(t.txn_id)  AS txn_count
FROM devices d LEFT JOIN transactions t USING (device_id)
WHERE d.status = 'online'
GROUP BY d.device_id, d.model, d.location, d.last_online
HAVING MAX(t.txn_time) IS NULL
    OR MAX(t.txn_time) < TIMESTAMP '2026-09-30 23:59:59' - INTERVAL '3 days'
ORDER BY last_txn_time NULLS FIRST;

-- 3. MTTR (fault → resolve) по моделям, часы. Бизнес: какие модели восстанавливаются дольше всего.
SELECT d.model,
       COUNT(*) AS tickets,
       ROUND(AVG(EXTRACT(EPOCH FROM (m.resolve_time - m.fault_time)) / 3600)::numeric, 2) AS mttr_hours
FROM maintenance m JOIN devices d USING (device_id)
GROUP BY d.model
ORDER BY mttr_hours DESC;

-- 3b. MTTR по типу неисправности (для вывода про выезд сетевых/аппаратных инженеров).
SELECT m.fault_type,
       COUNT(*) AS tickets,
       ROUND(AVG(EXTRACT(EPOCH FROM (m.resolve_time - m.fault_time)) / 3600)::numeric, 2) AS mttr_hours
FROM maintenance m JOIN devices d USING (device_id)   -- JOIN отсекает заявки на несуществующие устройства, как и в п. 3
GROUP BY m.fault_type
ORDER BY mttr_hours DESC;

-- 4. Топ-5 кодов ошибок среди failed. Бизнес: на какие причины отказов направить ремонт/прошивку.
SELECT error_code, COUNT(*) AS failed_txns,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS share_pct
FROM transactions
WHERE status = 'failed'
GROUP BY error_code
ORDER BY failed_txns DESC
LIMIT 5;

-- 5. Временные аномалии в заявках: resolve_time раньше dispatch_time. Бизнес: ошибки меток времени в системе заявок искажают MTTR.
SELECT ticket_id, device_id, dispatch_time, resolve_time,
       ROUND(EXTRACT(EPOCH FROM (dispatch_time - resolve_time)) / 60) AS minutes_resolve_before_dispatch
FROM anomaly_maintenance
WHERE resolve_time < dispatch_time
ORDER BY ticket_id;

-- 6. Заявки на несуществующие устройства. Бизнес: инженеры выезжали на устройства, которых нет в мониторинге (ошибка справочника).
SELECT m.ticket_id, m.device_id, m.fault_time, m.fault_type
FROM maintenance m LEFT JOIN devices d USING (device_id)
WHERE d.device_id IS NULL
ORDER BY m.ticket_id;

-- 7. Средний остаток наличных по регионам. Бизнес: планирование маршрутов инкассации.
SELECT split_part(location, ',', 1) AS region,
       COUNT(*)                     AS devices,
       ROUND(AVG(cash_level), 1)    AS avg_cash_pct
FROM devices
WHERE cash_level IS NOT NULL
GROUP BY 1
ORDER BY avg_cash_pct ASC;

-- 8. Устройства с остатком наличных < 20 %. Бизнес: риск остановки обслуживания — внеплановая инкассация.
SELECT device_id, location, model, status, cash_level
FROM devices
WHERE cash_level < 20
ORDER BY cash_level;

-- 9. Динамика транзакций по дням (для линейного графика). Бизнес: нагрузка и провалы по дням месяца.
SELECT txn_time::date AS day,
       COUNT(*)                                         AS txns,
       COUNT(*) FILTER (WHERE status = 'success')       AS success_txns
FROM transactions
GROUP BY 1
ORDER BY 1;

-- 10. Доля timeout по моделям. Бизнес: timeout указывает на сеть/процессинг, а не на «железо».
SELECT d.model,
       COUNT(*) AS txns,
       COUNT(*) FILTER (WHERE t.status = 'timeout') AS timeouts,
       ROUND(100.0 * COUNT(*) FILTER (WHERE t.status = 'timeout') / COUNT(*), 1) AS timeout_pct
FROM transactions t JOIN devices d USING (device_id)
GROUP BY d.model
ORDER BY timeout_pct DESC;

-- 11. Расхождение «устройство online, но нет транзакций за период» (вообще ни одной). Бизнес: новые или «мёртвые» терминалы в мониторинге.
SELECT d.device_id, d.model, d.location, d.last_online
FROM devices d
WHERE d.status = 'online'
  AND NOT EXISTS (SELECT 1 FROM transactions t WHERE t.device_id = d.device_id)
ORDER BY d.device_id;

-- 12. Топ-3 модели по количеству инцидентов. Бизнес: куда направлять ресурс сервиса в первую очередь.
SELECT d.model, COUNT(*) AS incidents,
       COUNT(DISTINCT d.device_id) AS devices_affected
FROM maintenance m JOIN devices d USING (device_id)
GROUP BY d.model
ORDER BY incidents DESC
LIMIT 3;
