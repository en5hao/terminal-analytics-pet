#!/usr/bin/env python3
"""Генерация «грязных» синтетических данных для пет-проекта
«Аналитика терминального оборудования».

Запуск:  python scripts/generate_data.py
Результат: data/raw/transactions.csv, device_status.csv, maintenance.csv
Данные воспроизводимы (фиксированный seed).
"""
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

SEED = 42
PERIOD_START = datetime(2026, 9, 1, 0, 0, 0)
SNAPSHOT = datetime(2026, 9, 30, 23, 59, 59)   # «момент выгрузки» всех трёх систем
OUT = Path(__file__).resolve().parent.parent / "data" / "raw"

random.seed(SEED)

# ---------------------------------------------------------------- устройства
LOCATIONS = [
    "Москва, Тверская", "Москва, Арбат", "Москва, Новослободская", "Москва, Ленинградский пр-т",
    "Москва, Кутузовский пр-т", "Москва, Профсоюзная",
    "Санкт-Петербург, Невский пр-т", "Санкт-Петербург, Московский пр-т",
    "Санкт-Петербург, Лиговский пр-т", "Санкт-Петербург, Большой пр-т",
    "Казань, Баумана", "Казань, Кремлёвская", "Казань, Пушкина", "Казань, Чистопольская",
    "Екатеринбург, Ленина", "Екатеринбург, Малышева", "Екатеринбург, 8 Марта", "Екатеринбург, Вайнера",
    "Новосибирск, Красный пр-т", "Новосибирск, Ленина", "Новосибирск, Гоголя", "Новосибирск, Дуси Ковальчук",
    "Нижний Новгород, Большая Покровская", "Нижний Новгород, Рождественская", "Нижний Новгород, Белинского",
    "Самара, Ленинградская", "Самара, Куйбышева", "Самара, Молодогвардейская",
    "Ростов-на-Дону, Садовая", "Ростов-на-Дону, Будённовский", "Ростов-на-Дону, Пушкинская",
    "Краснодар, Красная", "Краснодар, Северная", "Краснодар, Гимназическая",
    "Воронеж, Плехановская", "Воронеж, Кольцовская", "Воронеж, Революции",
    "Уфа, Ленина", "Уфа, Чернышевского", "Уфа, Мингажева",
]
N_DEV = 40
MODELS = ["Model-X", "Model-Y", "Model-Z"]
dev_ids = [f"ATM-{i:03d}" for i in range(1, N_DEV + 1)]

NEW_DEVICES = {"ATM-038", "ATM-039", "ATM-040"}            # есть только в мониторинге
LIARS = {"ATM-007": datetime(2026, 9, 24, 11, 40),          # online, но давно нет связи
         "ATM-014": datetime(2026, 9, 25, 16, 5),
         "ATM-022": datetime(2026, 9, 26, 9, 15)}
OFFLINE = {"ATM-009": datetime(2026, 9, 18, 3, 10), "ATM-017": datetime(2026, 9, 21, 22, 30),
           "ATM-026": datetime(2026, 9, 12, 14, 0), "ATM-033": datetime(2026, 9, 27, 6, 45)}
MAINT = {"ATM-012": datetime(2026, 9, 29, 15, 20), "ATM-029": datetime(2026, 9, 30, 8, 0)}
LOW_CASH = {"ATM-003": 12, "ATM-019": 17, "ATM-031": 18}
BAD_CASH = {"ATM-021": 135, "ATM-035": -5}                   # аномалии остатка

devices = []
for i, d in enumerate(dev_ids):
    model = MODELS[i % 3] if i % 5 else "Model-X"
    if d in LIARS:
        status, last = "online", LIARS[d]
    elif d in OFFLINE:
        status, last = "offline", OFFLINE[d]
    elif d in MAINT:
        status, last = "maintenance", MAINT[d]
    else:
        status = "online"
        last = SNAPSHOT - timedelta(minutes=random.randint(2, 600))
    cash = LOW_CASH.get(d, BAD_CASH.get(d, random.randint(28, 96)))
    devices.append(dict(device_id=d, location=LOCATIONS[i], model=model,
                        last_online=last.strftime("%Y-%m-%d %H:%M:%S"),
                        status=status, cash_level=cash))
devices.append(dict(devices[4]))   # дубликат строки в мониторинге (грязь)
dev_info = {x["device_id"]: x for x in devices}

# --------------------------------------------------------------- транзакции
FAIL_P = {"Model-X": (0.10, 0.06), "Model-Y": (0.035, 0.02), "Model-Z": (0.03, 0.06)}  # (failed, timeout)
ERR = {"Model-X": ["E01"] * 6 + ["E02"] * 3 + ["E03"],
       "Model-Y": ["E01"] * 2 + ["E02"] * 3 + ["E03"] * 4,
       "Model-Z": ["E01"] * 2 + ["E02"] * 2 + ["E03"] * 5}
TYPES = (["снятие"] * 55 + ["внесение"] * 15 + ["запрос баланса"] * 20 + ["перевод"] * 10)

def rand_time(a, b):
    sec = int((b - a).total_seconds())
    t = a + timedelta(seconds=random.randint(0, sec))
    # деловая активность: 7–23 ч
    return t.replace(hour=random.randint(7, 22), minute=random.randint(0, 59), second=random.randint(0, 59)) \
        if random.random() < 0.9 else t

active = [d for d in dev_ids if d not in NEW_DEVICES]
txns = []
tid = 0
def make_txn(dev, when):
    global tid
    tid += 1
    m = dev_info[dev]["model"]
    pf, pt = FAIL_P[m]
    r = random.random()
    status = "failed" if r < pf else "timeout" if r < pf + pt else "success"
    ttype = random.choice(TYPES)
    amount = 0 if ttype == "запрос баланса" else random.choice([500, 1000, 1500, 2000, 3000, 5000, 7000, 10000, 15000])
    return dict(txn_id=f"T{tid:06d}", device_id=dev, txn_time=when, txn_type=ttype, amount=amount,
                status=status, error_code=random.choice(ERR[m]) if status == "failed" else "")

for d in active:
    end = datetime.strptime(dev_info[d]["last_online"], "%Y-%m-%d %H:%M:%S") if d in {**LIARS, **OFFLINE, **MAINT} else SNAPSHOT
    days = (end - PERIOD_START).total_seconds() / 86400
    n = max(3, int(random.gauss(19, 4) * days / 30))
    times = [rand_time(PERIOD_START, end - timedelta(minutes=5)) for _ in range(n)]
    if d not in LIARS and d not in OFFLINE and d not in MAINT:   # «живое» устройство транзакции в последние 3 дня
        times.append(rand_time(SNAPSHOT - timedelta(days=2), SNAPSHOT - timedelta(hours=1)))
    for t in times:
        if t > end: t = end - timedelta(minutes=random.randint(10, 400))
        txns.append(make_txn(d, t))
random.shuffle(txns)
txns.sort(key=lambda x: x["txn_time"])
for i, x in enumerate(txns, 1):      # сквозные ID по времени
    x["txn_id"] = f"T{i:06d}"

# «грязь» в транзакциях
n = len(txns)
def pick(frac, exclude=()):
    pool = [i for i in range(n) if i not in exclude]
    return set(random.sample(pool, max(1, round(n * frac))))
used = set()
alt_fmt = pick(0.05);                     used |= alt_fmt
no_time = pick(0.02, used);               used |= no_time
typo = pick(0.01);
null_amt = pick(0.02, {i for i in range(n) if txns[i]["txn_type"] == "запрос баланса"})
neg_amt = pick(0.01, {i for i in range(n) if txns[i]["txn_type"] == "запрос баланса"} | null_amt)
rows = []
for i, x in enumerate(txns):
    r = dict(x)
    t = x["txn_time"]
    r["txn_time"] = (f"{t.year}/{t.month}/{t.day} {t.hour}:{t.minute:02d}" if i in alt_fmt
                     else "" if i in no_time else t.strftime("%Y-%m-%d %H:%M:%S"))
    if i in typo and r["txn_type"] == "снятие": r["txn_type"] = "снятиее"
    if i in null_amt: r["amount"] = ""
    if i in neg_amt: r["amount"] = -abs(r["amount"])
    rows.append(r)
# 1–2 опечатки гарантированно
for r in rows:
    if r["txn_type"] == "снятие" and sum(1 for z in rows if z["txn_type"] == "снятиее") < 5:
        r["txn_type"] = "снятиее"
# полные дубли строк (чтобы шаг «удалить дубликаты по txn_id» был осмысленным)
for r in random.sample(rows, 6):
    rows.append(dict(r))
rows.sort(key=lambda r: r["txn_id"])

# -------------------------------------------------------------- заявки
FT = {"hardware": (3, 10), "software": (1, 4), "network": (2, 9)}
faulty = ["ATM-005", "ATM-010", "ATM-015", "ATM-020", "ATM-025", "ATM-030", "ATM-035", "ATM-001", "ATM-002",
          "ATM-004", "ATM-006", "ATM-008", "ATM-011", "ATM-013", "ATM-016", "ATM-018", "ATM-023", "ATM-024",
          "ATM-027", "ATM-028", "ATM-032", "ATM-034", "ATM-036", "ATM-037", "ATM-012", "ATM-029", "ATM-009", "ATM-017"]
tickets = []
for i in range(1, 31):
    dev = faulty[i - 1] if i - 1 < len(faulty) else random.choice(dev_ids[:37])
    ft = random.choice(["hardware", "software", "network"])
    fault = PERIOD_START + timedelta(days=random.randint(0, 28), hours=random.randint(7, 20), minutes=random.randint(0, 59))
    disp = fault + timedelta(minutes=random.randint(45, 240))
    lo, hi = FT[ft]
    res = disp + timedelta(minutes=random.randint(int(lo * 30), int(hi * 30)))
    tickets.append(dict(ticket_id=f"M{i:04d}", device_id=dev, fault_time=fault, dispatch_time=disp,
                        resolve_time=res, fault_type=ft))
tickets[4]["device_id"] = "ATM-051"      # несуществующие устройства
tickets[22]["device_id"] = "ATM-099"
for k in (11, 17):                       # M0012, M0018: решение раньше выезда
    t = tickets[k]
    t["resolve_time"] = t["dispatch_time"] - timedelta(minutes=random.randint(20, 90))
for t in tickets:
    for f in ("fault_time", "dispatch_time", "resolve_time"):
        t[f] = t[f].strftime("%Y-%m-%d %H:%M:%S")

# -------------------------------------------------------------- запись
def write(name, fields, data):
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / name, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(data)
    print(f"{name}: {len(data)} строк")

write("transactions.csv", ["txn_id", "device_id", "txn_time", "txn_type", "amount", "status", "error_code"], rows)
write("device_status.csv", ["device_id", "location", "model", "last_online", "status", "cash_level"], devices)
write("maintenance.csv", ["ticket_id", "device_id", "fault_time", "dispatch_time", "resolve_time", "fault_type"], tickets)
