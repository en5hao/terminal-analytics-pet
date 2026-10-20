#!/usr/bin/env python3
"""Сборка report/terminal_analysis_report.pdf (7 страниц) из data/clean и screenshots/."""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle,
                                Image, PageBreak, KeepTogether)
from metrics import compute

ROOT = Path(__file__).resolve().parent.parent
FD = "/usr/share/fonts/truetype/dejavu/"
pdfmetrics.registerFont(TTFont("DV", FD + "DejaVuSans.ttf")); pdfmetrics.registerFont(TTFont("DVB", FD + "DejaVuSans-Bold.ttf"))
pdfmetrics.registerFontFamily("DV", normal="DV", bold="DVB")
NAVY, RED, GREY = colors.HexColor("#1F3A5F"), colors.HexColor("#C8442F"), colors.HexColor("#6B7280")
H1 = ParagraphStyle("h1", fontName="DVB", fontSize=17, leading=22, textColor=NAVY, spaceAfter=8)
H2 = ParagraphStyle("h2", fontName="DVB", fontSize=11.5, leading=15, textColor=NAVY, spaceBefore=8, spaceAfter=4)
P = ParagraphStyle("p", fontName="DV", fontSize=9.5, leading=13.5, spaceAfter=4)
SM = ParagraphStyle("sm", parent=P, fontSize=8, leading=11, textColor=GREY)
BUL = ParagraphStyle("b", parent=P, leftIndent=12, bulletIndent=2, spaceAfter=3)
TC = ParagraphStyle("tc", fontName="DV", fontSize=8.2, leading=10.5)

k, D = compute(); L = k["cleaning"]
GH = "https://github.com/en5hao/terminal-analytics-pet"

def tbl(rows, widths, head=True, hl=None):
    data = [[Paragraph(str(c), TC) for c in r] for r in rows]
    t = Table(data, colWidths=[w * mm for w in widths], repeatRows=1 if head else 0)
    st = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D5DAE1")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if head:
        st += [("BACKGROUND", (0, 0), (-1, 0), NAVY)]
        for i, c in enumerate(rows[0]): data[0][i] = Paragraph(f'<font color="white"><b>{c}</b></font>', TC)
        t = Table(data, colWidths=[w * mm for w in widths], repeatRows=1)
    if hl: st += [("BACKGROUND", (0, r), (-1, r), colors.HexColor("#FBE9E6")) for r in hl]
    t.setStyle(TableStyle(st)); return t

def bullets(items): return [Paragraph(i, BUL, bulletText="•") for i in items]
def img(path, w_mm):
    from PIL import Image as PI
    w, h = PI.open(path).size
    return Image(str(path), width=w_mm * mm, height=w_mm * mm * h / w)

# --- график для стр. 4
daily = pd.DataFrame(k["daily"]); daily["d"] = pd.to_datetime(daily["txn_time"])
fig, ax = plt.subplots(figsize=(8, 2.5)); plt.rcParams["font.family"] = "DejaVu Sans"
ax.plot(daily["d"], daily["n"], color="#2F6DB5", lw=2); ax.fill_between(daily["d"], daily["n"], alpha=.1, color="#2F6DB5")
ax.xaxis.set_major_locator(mdates.DayLocator(interval=3)); ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
ax.set_title("Транзакции по дням, сентябрь 2026", loc="left", fontsize=10, color="#1F3A5F"); ax.grid(alpha=.25)
for s in ("top", "right"): ax.spines[s].set_visible(False)
fig.tight_layout(); fig.savefig("/tmp/daily.png", dpi=150); plt.close(fig)

bm, mt, mo = k["by_model"], k["mttr_by_type"], k["mttr_by_model"]
dc, am = D["dc"], D["am"]
story = []

# ---- 1. Титул
story += [Spacer(1, 55 * mm), Paragraph("Аналитика терминального оборудования", ParagraphStyle("t", parent=H1, fontSize=26, leading=32)),
          Paragraph("Сквозной кейс: очистка трёх источников → SQL-анализ → дашборд Power BI → выводы и рекомендации", ParagraphStyle("st", parent=P, fontSize=12, leading=17, textColor=GREY)),
          Spacer(1, 25 * mm),
          Paragraph("<b>Автор:</b> Энола Ширманова", P),
          Paragraph("РТУ МИРЭА, Институт кибербезопасности и цифровых технологий", P),
          Paragraph("<b>Дата:</b> 19.10.2026", P),
          Paragraph("<b>Период данных:</b> 01.09.2026 — 30.09.2026 (данные синтетические)", P),
          Paragraph(f'<b>GitHub:</b> <link href="{GH}" color="#2F6DB5">{GH}</link>', P),
          PageBreak()]

# ---- 2. Контекст
story += [Paragraph("1. Контекст и данные", H1),
          Paragraph("Сервисное подразделение ИТ-компании обслуживает сеть банкоматов и платёжных терминалов заказчика. "
                    "Данные лежат в трёх несинхронизированных системах. Задача: свести их, найти расхождения, посчитать "
                    "KPI и объяснить заказчику каждую цифру.", P),
          Paragraph("Источники", H2),
          tbl([["Система", "Файл", "Строк (сырых)", "Что содержит"],
               ["Процессинг", "transactions.csv", L["transactions_raw"], "Журнал операций: устройство, время, тип, сумма, статус, код ошибки"],
               ["Мониторинг", "device_status.csv", L["devices_raw"], "Статус терминала, модель, адрес, last_online, остаток наличных"],
               ["Заявки", "maintenance.csv", L["maint_raw"], "Инциденты и выезды: fault/dispatch/resolve, тип неисправности"]], [28, 38, 26, 88]),
          Paragraph("Проблемы качества, заложенные в исходные данные", H2)]
story += bullets([
    "Транзакции: два формата времени (<i>2026-09-01 08:23:11</i> и <i>2026/9/1 8:23</i>), пустое время, пропуски и отрицательные значения в сумме, опечатка «снятиее», полные дубли строк.",
    "Мониторинг: остаток наличных вне диапазона 0–100, дубль строки устройства, три устройства только в мониторинге (без транзакций), три устройства «online» без связи более 3 дней.",
    "Заявки: две заявки на несуществующие устройства, две заявки с resolve_time раньше dispatch_time."])
story += [Paragraph("Допущения", H2)]
story += bullets([
    "«Момент выгрузки» всех систем = 30.09.2026 23:59:59. Все сравнения «старше 3 дней» делаются относительно него, а не относительно текущей даты.",
    "Коэффициент успешности = доля транзакций со статусом <i>success</i>. Ошибка = <i>failed</i> + <i>timeout</i>.",
    "MTTR = среднее время от fault_time до resolve_time в часах; заявки на несуществующие устройства и с аномальными метками времени в расчёт не входят."])
story += [PageBreak()]

# ---- 3. Очистка
story += [Paragraph("2. Очистка в Power Query", H1),
          Paragraph("Все шаги описаны на языке M в <i>power_query/queries.txt</i> и воспроизведены скриптом <i>scripts/clean_data.py</i>; результаты совпадают.", P),
          tbl([["Этап", "Действие", "Затронуто строк"],
               ["transactions", "Удалены дубли по txn_id", L["txn_duplicates_removed"]],
               ["transactions", "Нет времени (вынесены, не учитываются в KPI)", L["txn_time_missing_quarantined"]],
               ["transactions", "Исправлена опечатка «снятиее» → «снятие»", L["txn_typos_fixed"]],
               ["transactions", "Нет суммы — исключены как неполные", L["txn_amount_null_removed"]],
               ["transactions", "Отрицательная сумма — в отдельный запрос anomaly_amount", L["txn_amount_negative_quarantined"]],
               ["transactions", f"Итого: {L['transactions_raw']} → <b>{L['transactions_clean']}</b>", ""],
               ["device_status", "Удалён дубль устройства", L["device_duplicates_removed"]],
               ["device_status", "cash_level вне 0–100 → null (ATM-021: 135, ATM-035: −5)", L["cash_level_out_of_range"]],
               ["maintenance", "resolve_time раньше dispatch_time → anomaly_maintenance", L["maint_time_anomalies"]],
               ["maintenance", "Несуществующий device_id → помечено", L["maint_orphan_devices"]]], [28, 112, 40]),
          Spacer(1, 4 * mm),
          Paragraph("Ключевой запрос device_consistency", H2),
          Paragraph("Транзакции сворачиваются до одной строки на устройство (число операций, время последней), затем левое соединение с "
                    "очищенным мониторингом. Так каждое устройство остаётся в одной строке, а устройства без транзакций не теряются. "
                    "Затем для статуса <i>online</i> проверяются: давность last_online, наличие транзакций и давность последней транзакции.", P),
          img(ROOT / "screenshots/power_query/pq_anomaly.png", 170),
          Paragraph("Рисунок: рендер строк device_consistency с аномалиями (замените скриншотом из Power Query).", SM),
          PageBreak()]

# ---- 4. KPI
story += [Paragraph("3. Ключевые показатели", H1)]
cards = Table([[Paragraph(f'<font size=8 color="#6B7280">Success Rate</font><br/><font name="DVB" size=17 color="#1F3A5F">{k["success_rate"]:.1%}</font>', P),
                Paragraph(f'<font size=8 color="#6B7280">MTTR Hours</font><br/><font name="DVB" size=17 color="#1F3A5F">{k["mttr_hours"]:.2f}</font>', P),
                Paragraph(f'<font size=8 color="#6B7280">Anomaly Devices</font><br/><font name="DVB" size=17 color="#C8442F">{k["anomaly_devices"]}</font>', P),
                Paragraph(f'<font size=8 color="#6B7280">Total Txns</font><br/><font name="DVB" size=17 color="#1F3A5F">{k["total_txns"]}</font>', P)]],
              colWidths=[45 * mm] * 4)
cards.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), .5, colors.HexColor("#D5DAE1")), ("INNERGRID", (0, 0), (-1, -1), .5, colors.HexColor("#D5DAE1")),
                           ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
story += [cards, Spacer(1, 3 * mm),
          tbl([["KPI", "Как считается", "Откуда"],
               ["Success Rate", f"success / все транзакции = {int(round(k['success_rate'] * k['total_txns']))} / {k['total_txns']}", "transactions_clean; SQL п. 1; DAX [Success Rate]"],
               ["MTTR Hours", f"среднее (resolve − fault) по {k['mttr_tickets']} заявкам, ч", "maintenance_clean + devices; SQL п. 3; DAX [MTTR Hours]"],
               ["Anomaly Devices", "устройства со статусом online и расхождением между системами", "device_consistency; SQL п. 2, 11"],
               ["Total Txns", "строки transactions_clean", "SQL п. 9; DAX [Total Txns]"]], [30, 85, 65]),
          Spacer(1, 3 * mm), img("/tmp/daily.png", 165),
          Paragraph("Показатели по моделям", H2),
          tbl([["Модель", "Транзакций", "Success Rate", "failed", "timeout", "Ошибки (failed+timeout)", "MTTR, ч (заявок)"]] +
              [[m_, int(bm[m_]["txns"]), f'{bm[m_]["success_rate"]:.1%}', f'{bm[m_]["failed_rate"]:.1%}', f'{bm[m_]["timeout_rate"]:.1%}',
                f'{bm[m_]["error_rate"]:.1%}', f'{mo[m_]["mean"]:.2f} ({int(mo[m_]["count"])})'] for m_ in sorted(bm)], [20, 26, 26, 18, 18, 38, 34],
              hl=[1]),
          PageBreak()]

# ---- 5. Расхождения
dd = dc[dc.anomaly_reason != "норма"].sort_values("anomaly_reason")
rows = [["device_id", "Модель", "last_online", "Последняя транзакция", "Транз.", "Причина"]]
for r in dd.itertuples():
    rows.append([r.device_id, r.model, r.last_online.strftime("%d.%m %H:%M"),
                 "—" if pd.isna(r.last_txn_time) else r.last_txn_time.strftime("%d.%m %H:%M"), r.txn_count, r.anomaly_reason])
story += [Paragraph("4. Расхождения между системами", H1),
          Paragraph("Устройства «online» в мониторинге, но без подтверждения процессингом", H2), tbl(rows, [20, 18, 28, 34, 14, 66]),
          Paragraph("Три устройства (ATM-007, ATM-014, ATM-022) не выходили на связь от 4,6 до 6,5 суток к моменту выгрузки (без транзакций 5,4–7,4 суток), но мониторинг показывает их как online. "
                    "Три новых устройства в Уфе (ATM-038…040) в мониторинге есть, транзакций нет — вероятно, не введены в эксплуатацию.", P),
          Paragraph("Заявки с ошибками данных", H2)]
am2 = am.copy()
rows = [["ticket_id", "device_id", "dispatch_time", "resolve_time", "Проблема"]]
for r in am2.itertuples():
    rows.append([r.ticket_id, r.device_id, r.dispatch_time.strftime("%d.%m %H:%M"), r.resolve_time.strftime("%d.%m %H:%M"), r.anomaly_reason])
story += [tbl(rows, [20, 22, 34, 34, 70]),
          Paragraph("Остатки наличных", H2)]
story += bullets([f'Остаток &lt; 20%: ' + ", ".join(f'{x["device_id"]} ({x["cash_level"]:.0f}%)' for x in k["low_cash"]) + ".",
                  "Некорректные значения датчика: ATM-021 (135%), ATM-035 (−5%) — заменены на null, требуют проверки."])
story += [PageBreak()]

# ---- 6. Выводы
top = k["top_error_devices"][0]
story += [Paragraph("5. Выводы и рекомендации", H1)]
story += bullets([
    f'<b>Model-X</b>: доля ошибок {bm["Model-X"]["error_rate"]:.1%} против {k["others_error_rate_vs_X"]:.1%} у остальных моделей (по парку {k["fleet_error_rate"]:.1%}) — проверить прошивку и партию. '
    f'Среди 10 устройств с наибольшим числом ошибок 7 — Model-X; худшее: {top["device_id"]} ({top["success_rate"]:.1%} успешных операций из {int(top["txns"])}).',
    f'<b>Model-Z</b>: доля timeout {bm["Model-Z"]["timeout_rate"]:.1%} при failed всего {bm["Model-Z"]["failed_rate"]:.1%} — похоже на сеть/процессинг, а не на «железо»; проверить каналы связи.',
    '<b>ATM-007, ATM-014, ATM-022</b> числятся online, но без связи 4,6–6,5 суток и без транзакций 5,4–7,4 суток — проверить сетевой мониторинг: статус online не подтверждается ни last_online, ни процессингом.',
    '<b>ATM-038, ATM-039, ATM-040</b> (Уфа): online, транзакций нет — подтвердить ввод в эксплуатацию либо вывести из отчётов по доступности.',
    f'<b>MTTR</b> по парку {k["mttr_hours"]:.1f} ч: hardware {mt["hardware"]["mean"]:.1f} ч, network {mt["network"]["mean"]:.1f} ч, software {mt["software"]["mean"]:.1f} ч — '
    f'аппаратные и сетевые инциденты чинятся дольше всего; проверить запас запчастей и схему выезда. По моделям выше всех Model-Y ({mo["Model-Y"]["mean"]:.1f} ч), но выборка мала ({int(mo["Model-Y"]["count"])} заявок).',
    '<b>M0012, M0018</b>: resolve_time раньше dispatch_time — проверить метки времени в системе заявок; <b>M0005, M0023</b> оформлены на несуществующие ATM-051 и ATM-099 — исправить справочник устройств.',
    '<b>Инкассация</b>: ATM-003 (12%), ATM-019 (17%), ATM-031 (18%) — внеплановый выезд; ATM-031 одновременно имеет худший Success Rate. Москва — регион с самым низким средним остатком (35%).'])
story += [Paragraph("Ограничения", H2)]
story += bullets(["Данные синтетические, выборка небольшая (26 заявок для MTTR) — выводы иллюстрируют метод.",
                  f"{L['txn_amount_null_removed']} транзакций без суммы исключены из всех расчётов (как неполные); если они реальные, Success Rate может сместиться."])
story += [PageBreak()]

# ---- 7. Приложение
story += [Paragraph("Приложение. Результаты SQL и Power Query", H1),
          img(ROOT / "screenshots/sql/query_success_rate.png", 165), Spacer(1, 3 * mm),
          img(ROOT / "screenshots/sql/query_anomaly_devices.png", 165), Spacer(1, 3 * mm),
          img(ROOT / "screenshots/power_query/pq_merge.png", 170),
          Paragraph("Изображения — рендеры результатов; для публикации замените реальными скриншотами.", SM)]

def deco(c, doc):
    c.saveState(); c.setFont("DV", 7.5); c.setFillColor(GREY)
    if doc.page > 1:
        c.drawString(15 * mm, 9 * mm, "Аналитика терминального оборудования — пет-проект, Э. Ширманова")
        c.drawRightString(195 * mm, 9 * mm, f"{doc.page}")
    c.restoreState()

doc = BaseDocTemplate(str(ROOT / "report" / "terminal_analysis_report.pdf"), pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm,
                      topMargin=15 * mm, bottomMargin=16 * mm, title="Аналитика терминального оборудования", author="Энола Ширманова")
doc.addPageTemplates([PageTemplate(id="p", frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")], onPage=deco)])
doc.build(story); print("pdf ok")
