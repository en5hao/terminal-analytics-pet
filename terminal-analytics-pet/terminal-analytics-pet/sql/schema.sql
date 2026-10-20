-- Схема БД terminal_analytics (PostgreSQL 14+)
-- Запуск:  createdb terminal_analytics && psql -d terminal_analytics -f sql/schema.sql
--          psql -d terminal_analytics -f sql/load.sql   (из корня репозитория)

DROP TABLE IF EXISTS anomaly_maintenance, maintenance, transactions, devices CASCADE;

CREATE TABLE devices (
  device_id   VARCHAR PRIMARY KEY,
  location    VARCHAR,
  model       VARCHAR,
  status      VARCHAR,
  last_online TIMESTAMP,
  cash_level  NUMERIC            -- NULL, если исходное значение вне 0–100 (аномалия)
);

CREATE TABLE transactions (
  txn_id     VARCHAR PRIMARY KEY,
  device_id  VARCHAR REFERENCES devices(device_id),
  txn_time   TIMESTAMP,
  txn_type   VARCHAR,
  amount     NUMERIC,
  status     VARCHAR,
  error_code VARCHAR              -- NULL, если операция не failed
);

-- Без FK на devices намеренно: в заявках есть несуществующие device_id,
-- их нужно ловить запросом (см. sql/queries.sql, п. 6).
CREATE TABLE maintenance (
  ticket_id     VARCHAR PRIMARY KEY,
  device_id     VARCHAR,
  fault_time    TIMESTAMP,
  dispatch_time TIMESTAMP,
  resolve_time  TIMESTAMP,
  fault_type    VARCHAR
);

-- Заявки, вынесенные Power Query как аномальные (resolve_time < dispatch_time
-- и несуществующие устройства). Нужна для запроса п. 5.
CREATE TABLE anomaly_maintenance (
  ticket_id      VARCHAR PRIMARY KEY,
  device_id      VARCHAR,
  fault_time     TIMESTAMP,
  dispatch_time  TIMESTAMP,
  resolve_time   TIMESTAMP,
  fault_type     VARCHAR,
  device_known   BOOLEAN,
  anomaly_reason VARCHAR
);
