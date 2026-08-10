#!/usr/bin/env python3
"""Import MMS By SKU monthly CSV (2026-01 ~ 2026-07) into P0068001 dashboard data.

CSV structure (UTF-16 LE, tab-separated):
  row0: metric names (GMV/Cust #/Parent Order #/quantity x7 months)
  row1: headers (Store/SKU/brand_chi/name/subcats/rmcode + Jan-Jul 2026 x4 metrics)
  row2+: data rows
  cols: 0=store 1=SKU 2=brand 3=name 4-8=cats 9-15=GMV 16-22=Cust# 23-29=Order# 30-36=qty 37-40=totals
"""
import csv
import io
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")
MONTHLY_META_PATH = os.path.join(DATA_DIR, "monthly_reports.json")
MONTHLY_SKU_PATH = os.path.join(DATA_DIR, "monthly_sku_data.js")

MONTHS = ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06", "2026-07"]
MONTH_LABELS = ["1月 2026", "2月 2026", "3月 2026", "4月 2026", "5月 2026", "6月 2026", "7月 2026"]


def load_csv(path):
    with open(path, "r", encoding="utf-16-le", errors="replace") as f:
        content = f.read()
    content = content.lstrip("\ufeff").replace("\x00", "")
    reader = csv.reader(io.StringIO(content), delimiter="\t")
    rows = list(reader)
    data = [r for r in rows[2:] if len(r) > 9 and r[1].strip()]
    return data


def parse_num(s):
    s = (s or "").replace(",", "").strip()
    if not s:
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def main():
    if len(sys.argv) < 2:
        print("Usage: import_monthly_csv.py <csv_path>")
        sys.exit(1)
    csv_path = sys.argv[1]
    rows = load_csv(csv_path)
    print(f"Loaded {len(rows)} SKU rows from CSV")

    # Per-month totals
    month_totals = {m: {"gmv": 0.0, "orders": 0, "qty": 0} for m in MONTHS}
    # Per-SKU per-month data
    sku_map = {}  # sku -> {brand, name, gmv[7], qty[7]}

    for r in rows:
        sku = r[1].strip()
        if not sku:
            continue
        brand = r[2].strip() if len(r) > 2 else ""
        name = r[3].strip() if len(r) > 3 else ""
        if sku not in sku_map:
            sku_map[sku] = {"brand": brand, "name": name, "gmv": [0.0] * 7, "qty": [0] * 7}
        info = sku_map[sku]
        for i in range(7):
            g = parse_num(r[9 + i]) if len(r) > 9 + i else 0.0
            q = parse_num(r[30 + i]) if len(r) > 30 + i else 0.0
            info["gmv"][i] += g
            info["qty"][i] += int(q)
            month_totals[MONTHS[i]]["gmv"] += g
            month_totals[MONTHS[i]]["qty"] += int(q)
            if len(r) > 23 + i:
                month_totals[MONTHS[i]]["orders"] += int(parse_num(r[23 + i]))

    # Round gmv
    for m in MONTHS:
        month_totals[m]["gmv"] = round(month_totals[m]["gmv"], 2)

    # Print summary
    print("\n=== Monthly Totals ===")
    for m in MONTHS:
        t = month_totals[m]
        print(f"{m}: GMV ${t['gmv']:,.2f} | Orders {t['orders']} | Qty {t['qty']}")

    # 1) Update monthly_reports.json (add 2026-01..07 before existing 2026-08)
    if os.path.exists(MONTHLY_META_PATH):
        with open(MONTHLY_META_PATH, encoding="utf-8") as f:
            meta = json.load(f)
    else:
        meta = []
    existing = {m["month"] for m in meta}
    new_entries = []
    for i, m in enumerate(MONTHS):
        if m in existing:
            continue
        t = month_totals[m]
        new_entries.append({
            "month": m,
            "label": MONTH_LABELS[i],
            "gmv": f"${t['gmv']:,.2f}",
            "orders": t["orders"],
            "qty": t["qty"],
            "days": 0,  # no daily breakdown, monthly aggregate only
            "filename": "",  # no XLSX available for these months
        })
    meta = new_entries + meta  # newest first: 2026-07 ... 2026-01, then 2026-08
    meta.sort(key=lambda x: x["month"], reverse=True)
    with open(MONTHLY_META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"\nmonthly_reports.json: {len(meta)} entries ({len(new_entries)} added)")

    # 2) Generate monthly_sku_data.js (by SKU by month, 2026-01..07)
    sku_list = []
    for sku, info in sku_map.items():
        gmv_arr = [round(g, 2) for g in info["gmv"]]
        sku_list.append({
            "sku": sku,
            "brand": info["brand"],
            "name": info["name"],
            "gmv": gmv_arr,
            "qty": info["qty"],
        })
    # Sort by total GMV desc
    sku_list.sort(key=lambda s: sum(s["gmv"]), reverse=True)
    payload = {"months": MONTHS, "labels": MONTH_LABELS, "skus": sku_list}
    with open(MONTHLY_SKU_PATH, "w", encoding="utf-8") as f:
        f.write("window.monthlySkuData = ")
        json.dump(payload, f, ensure_ascii=False)
        f.write(";\n")
    print(f"monthly_sku_data.js: {len(sku_list)} SKUs x 7 months")


if __name__ == "__main__":
    main()
