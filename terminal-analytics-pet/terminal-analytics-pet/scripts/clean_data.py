#!/usr/bin/env python3
"""Воспроизведение очистки из power_query/queries.txt на pandas.

Нужен, чтобы (1) получить data/clean/*.csv без ручного клика по Power Query и
(2) сверить цифры: результат Power Query и этого скрипта должен совпасть.
Запуск: python scripts/clean_data.py
"""
import json
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW, CLEAN = ROOT / "data" / "raw", ROOT / "data" / "clean"
SNAPSHOT = datetime(2026, 9, 30, 23, 59, 59)   # момент выгрузки (параметр SnapshotDate в Power Query)
STALE = timedelta(days=3)
CLEAN.mkdir(parents=True, exist_ok=True)
log = {}

def parse_dt(s):
    """Два формата: 2026-09-01 08:23:11 и 2026/9/1 8:23; пустое -> NaT."""
    out = pd.to_datetime(s, format="%Y-%m-%d %H:%M:%S", errors="coerce")
    alt = pd.to_datetime(s, format="%Y/%m/%d %H:%M", errors="coerce")
    return out.fillna(alt)

# ------------------------------------------------------------ transactions
t = pd.read_csv(RAW / "transactions.csv", encoding="utf-8-sig", dtype=str)
log["transactions_raw"] = len(t)
t = t.drop_duplicates("txn_id");                                  log["txn_duplicates_removed"] = log["transactions_raw"] - len(t)
t["txn_time"] = parse_dt(t["txn_time"])
anom_time = t[t["txn_time"].isna()];                              log["txn_time_missing_quarantined"] = len(anom_time)
t = t[t["txn_time"].notna()]
t["txn_type"] = t["txn_type"].str.strip().replace({"снятиее": "снятие"})
log["txn_typos_fixed"] = int((pd.read_csv(RAW / "transactions.csv", encoding="utf-8-sig", dtype=str)
                              .drop_duplicates("txn_id")["txn_type"] == "снятиее").sum())
t["amount"] = pd.to_numeric(t["amount"], errors="coerce")
log["txn_amount_null_removed"] = int(t["amount"].isna().sum())
t = t[t["amount"].notna()]
anom_amount = t[t["amount"] < 0];                                 log["txn_amount_negative_quarantined"] = len(anom_amount)
t = t[t["amount"] >= 0]
t["error_code"] = t["error_code"].fillna("")
t = t.sort_values("txn_id")
log["transactions_clean"] = len(t)

# ----------------------------------------------------------- device_status
d = pd.read_csv(RAW / "device_status.csv", encoding="utf-8-sig")
log["devices_raw"] = len(d)
d = d.drop_duplicates("device_id");                               log["device_duplicates_removed"] = log["devices_raw"] - len(d)
d["last_online"] = parse_dt(d["last_online"].astype(str))
bad_cash = ~d["cash_level"].between(0, 100)
log["cash_level_out_of_range"] = int(bad_cash.sum())
d["cash_level_anomaly"] = bad_cash
d.loc[bad_cash, "cash_level"] = pd.NA
log["devices_clean"] = len(d)

# ------------------------------------------------------------- maintenance
m = pd.read_csv(RAW / "maintenance.csv", encoding="utf-8-sig")
for c in ("fault_time", "dispatch_time", "resolve_time"):
    m[c] = parse_dt(m[c].astype(str))
m["device_known"] = m["device_id"].isin(d["device_id"])
m["anomaly_reason"] = ""
m.loc[m["resolve_time"] < m["dispatch_time"], "anomaly_reason"] = "resolve_time раньше dispatch_time"
m.loc[~m["device_known"], "anomaly_reason"] = "несуществующий device_id"
anom_m = m[m["anomaly_reason"] != ""]
m_clean = m[m["resolve_time"] >= m["dispatch_time"]]             # временные аномалии вынесены; «сироты» остаются с device_known=False
log["maint_raw"] = len(m)
log["maint_time_anomalies"] = int((m["resolve_time"] < m["dispatch_time"]).sum())
log["maint_orphan_devices"] = int((~m["device_known"]).sum())
log["maint_clean"] = len(m_clean)

# ------------------------------------------------------ device_consistency
g = t.groupby("device_id").agg(txn_count=("txn_id", "count"), last_txn_time=("txn_time", "max")).reset_index()
dc = d.merge(g, on="device_id", how="left")                       # LEFT JOIN: все устройства мониторинга
dc["txn_count"] = dc["txn_count"].fillna(0).astype(int)
dc["days_since_last_online"] = ((SNAPSHOT - dc["last_online"]).dt.total_seconds() / 86400).round(1)
dc["days_since_last_txn"] = ((SNAPSHOT - dc["last_txn_time"]).dt.total_seconds() / 86400).round(1)

def reason(r):
    if r["status"] != "online":
        return "норма"
    if r["last_online"] < SNAPSHOT - STALE:
        return "онлайн, но нет подключения > 3 дней"
    if r["txn_count"] == 0:
        return "онлайн, но нет ни одной транзакции"
    if r["last_txn_time"] < SNAPSHOT - STALE:
        return "онлайн, но нет транзакций > 3 дней"
    return "норма"
dc["anomaly_reason"] = dc.apply(reason, axis=1)
log["anomaly_devices"] = int((dc["anomaly_reason"] != "норма").sum())
log["anomaly_by_reason"] = dc["anomaly_reason"].value_counts().to_dict()

# ------------------------------------------------------------------ запись
FMT = "%Y-%m-%d %H:%M:%S"
def save(df, name, dt_cols=()):
    df = df.copy()
    for c in dt_cols:
        df[c] = df[c].dt.strftime(FMT)
    df.to_csv(CLEAN / name, index=False, encoding="utf-8")

save(t, "transactions_clean.csv", ["txn_time"])
save(d.drop(columns="cash_level_anomaly"), "device_status_clean.csv", ["last_online"])
save(m_clean.drop(columns=["anomaly_reason", "device_known"]), "maintenance_clean.csv", ["fault_time", "dispatch_time", "resolve_time"])
save(dc, "device_consistency.csv", ["last_online", "last_txn_time"])
save(anom_amount, "anomaly_amount.csv", ["txn_time"])
save(anom_time, "anomaly_txn_time.csv")
save(anom_m, "anomaly_maintenance.csv", ["fault_time", "dispatch_time", "resolve_time"])
(CLEAN / "cleaning_log.json").write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(log, ensure_ascii=False, indent=2))
