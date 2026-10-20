"""Расчёт KPI и выводов по очищенным данным (источник цифр для PDF, README и Excel-сверки)."""
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
C = ROOT / "data" / "clean"

def load():
    t = pd.read_csv(C / "transactions_clean.csv", parse_dates=["txn_time"], keep_default_na=False, na_values=[""])
    d = pd.read_csv(C / "device_status_clean.csv", parse_dates=["last_online"])
    m = pd.read_csv(C / "maintenance_clean.csv", parse_dates=["fault_time", "dispatch_time", "resolve_time"])
    dc = pd.read_csv(C / "device_consistency.csv", parse_dates=["last_online", "last_txn_time"])
    am = pd.read_csv(C / "anomaly_maintenance.csv", parse_dates=["fault_time", "dispatch_time", "resolve_time"])
    log = json.loads((C / "cleaning_log.json").read_text(encoding="utf-8"))
    return t, d, m, dc, am, log

def compute():
    t, d, m, dc, am, log = load()
    x = t.merge(d[["device_id", "model", "location"]], on="device_id")
    mm = m.merge(d[["device_id", "model"]], on="device_id")          # inner: без «сирот»
    mm["mttr_h"] = (mm["resolve_time"] - mm["fault_time"]).dt.total_seconds() / 3600
    k = {}
    k["total_txns"] = len(t)
    k["success_rate"] = (t["status"] == "success").mean()
    k["mttr_hours"] = mm["mttr_h"].mean()
    k["mttr_tickets"] = len(mm)
    k["anomaly_devices"] = int((dc["anomaly_reason"] != "норма").sum())
    g = x.groupby("model").apply(lambda a: pd.Series({
        "txns": len(a), "success_rate": (a.status == "success").mean(),
        "failed_rate": (a.status == "failed").mean(), "timeout_rate": (a.status == "timeout").mean(),
        "error_rate": (a.status != "success").mean()}), include_groups=False)
    k["by_model"] = g.round(4).to_dict("index")
    k["fleet_error_rate"] = (t.status != "success").mean()
    k["others_error_rate_vs_X"] = (x[x.model != "Model-X"].status != "success").mean()
    k["mttr_by_type"] = mm.groupby("fault_type")["mttr_h"].agg(["mean", "count"]).round(2).to_dict("index")
    k["mttr_by_model"] = mm.groupby("model")["mttr_h"].agg(["mean", "count"]).round(2).to_dict("index")
    f = t[t.status == "failed"]
    k["error_codes"] = f["error_code"].value_counts().to_dict()
    k["x_e01_share"] = float((f.merge(d[["device_id", "model"]], on="device_id").query("model=='Model-X'").error_code == "E01").mean())
    k["low_cash"] = d[d.cash_level < 20][["device_id", "location", "cash_level"]].to_dict("records")
    k["bad_cash_devices"] = d[d.cash_level.isna()]["device_id"].tolist()
    k["daily"] = t.groupby(t.txn_time.dt.date).size().rename("n").reset_index().astype({"txn_time": str}).to_dict("records")
    dev = x.groupby("device_id").apply(lambda a: pd.Series({"txns": len(a), "errors": int((a.status != "success").sum()),
                                      "success_rate": (a.status == "success").mean()}), include_groups=False).reset_index()
    k["top_error_devices"] = dev.sort_values(["errors", "txns"], ascending=[False, False]).head(5).merge(
        d[["device_id", "model", "location"]], on="device_id").to_dict("records")
    k["cleaning"] = log
    return k, dict(t=t, d=d, m=m, dc=dc, am=am, x=x, mm=mm, dev=dev)

if __name__ == "__main__":
    k, _ = compute()
    print(json.dumps(k, ensure_ascii=False, indent=1, default=str))
