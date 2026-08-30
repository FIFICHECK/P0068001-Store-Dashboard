#!/usr/bin/env python3
"""
P0068001 — 將每日 order reports (sales_trend_data.js) aggregate 成月度 by-SKU，
更新 monthly_sku_data.json（「全部 SKU 明細」panel 用）。

背景 (2026-08-30):
- monthly_sku_data.json 原本靠 MMS by-SKU-by-month CSV import（MONTHS 寫死 1-7 月）
- 8 月起有每日 xlsx → process_data.py 生成 sales_trend_data.js (by SKU by daily)
- 呢個 script 由 sales_trend_data 砌返月度 by-SKU，merge 入 monthly_sku_data.json

用法:
    P0068001_BASE=/home/snkwok/dashboard-private-data/P0068001 python3.12 update_monthly_sku_data.py
    (唔 set env 就 default public repo — 向後兼容)
"""
import json
import os
import re
import sys

BASE = os.environ.get("P0068001_BASE", "/home/snkwok/P0068001-Store-Dashboard")
DATA_DIR = os.path.join(BASE, "data")
TREND_PATH = os.path.join(DATA_DIR, "sales_trend_data.js")
SKU_PATH = os.path.join(DATA_DIR, "monthly_sku_data.json")

MONTH_LABELS = {
    "2026-01": "1月 2026", "2026-02": "2月 2026", "2026-03": "3月 2026",
    "2026-04": "4月 2026", "2026-05": "5月 2026", "2026-06": "6月 2026",
    "2026-07": "7月 2026", "2026-08": "8月 2026", "2026-09": "9月 2026",
    "2026-10": "10月 2026", "2026-11": "11月 2026", "2026-12": "12月 2026",
}


def load_trend(path):
    with open(path, encoding="utf-8") as f:
        js = f.read()
    m = re.search(r"window\.salesTrendData\s*=\s*(\{.*?\});?\s*$", js, re.S)
    if not m:
        raise ValueError("sales_trend_data.js format 唔啱")
    return json.loads(m.group(1))


def main():
    trend = load_trend(TREND_PATH)
    dates = trend.get("dates", [])

    # 由 daily dates 分組做月度 by-SKU
    month_dates = {}
    for i, d in enumerate(dates):
        month_dates.setdefault(d[:7], []).append(i)

    # 每個月 by-SKU aggregate
    month_sku = {}  # month -> {sku: {gmv, qty, name}}
    for month, idxs in month_dates.items():
        agg = {}
        for s in trend.get("skus", []):
            g = sum(s["gmv"][i] for i in idxs)
            q = sum(s["qty"][i] for i in idxs)
            agg[s["sku"]] = {"gmv": g, "qty": q, "name": s.get("name", "")}
        month_sku[month] = agg

    # 讀現有 monthly_sku_data.json
    with open(SKU_PATH, encoding="utf-8") as f:
        sku_data = json.load(f)

    months = sku_data.get("months", [])
    labels = sku_data.get("labels", [])
    skus = sku_data.get("skus", [])

    # 加新月份
    new_months = [m for m in sorted(month_sku.keys()) if m not in months]
    if new_months:
        months.extend(new_months)
        labels.extend(MONTH_LABELS.get(m, m) for m in new_months)
        # 現有 skus 補 0
        for s in skus:
            s.setdefault("gmv", []).extend([0.0] * len(new_months))
            s.setdefault("qty", []).extend([0.0] * len(new_months))

    # 更新每隻 SKU 嘅月度值 + 加新 SKU
    existing = {s["sku"]: s for s in skus}
    new_sku_entries = []
    for month, agg in sorted(month_sku.items()):
        if month not in months:
            continue
        mi = months.index(month)
        for sku, v in agg.items():
            if sku in existing:
                s = existing[sku]
                while len(s["gmv"]) <= mi:
                    s["gmv"].append(0.0)
                    s["qty"].append(0.0)
                s["gmv"][mi] = v["gmv"]
                s["qty"][mi] = v["qty"]
            else:
                entry = {
                    "sku": sku,
                    "brand": "",
                    "name": v["name"],
                    "gmv": [0.0] * len(months),
                    "qty": [0.0] * len(months),
                }
                entry["gmv"][mi] = v["gmv"]
                entry["qty"][mi] = v["qty"]
                existing[sku] = entry
                new_sku_entries.append(entry)

    if new_sku_entries:
        skus.extend(new_sku_entries)

    # 按總 GMV desc 排序
    skus.sort(key=lambda s: sum(s.get("gmv", [])), reverse=True)

    sku_data["months"] = months
    sku_data["labels"] = labels
    sku_data["skus"] = skus

    with open(SKU_PATH, "w", encoding="utf-8") as f:
        json.dump(sku_data, f, ensure_ascii=False)

    # 驗證輸出
    print(f"months: {months}")
    print(f"labels: {labels}")
    print(f"skus: {len(skus)}（新增 {len(new_sku_entries)}）")
    total = sum(s.get("gmv", [0])[-1] for s in skus)
    print(f"最新月份總 GMV: ${total:,.2f}")
    total_qty = sum(s.get("qty", [0])[-1] for s in skus)
    print(f"最新月份總 QTY: {total_qty:,.0f}")


if __name__ == "__main__":
    main()
