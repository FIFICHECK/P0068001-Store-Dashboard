#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P0068001 Shelf Life Check — compare MMS Product export Minimum Shelf Life (DP, idx 119)
vs GreenLab.xlsx Sheet4 Column I (納入GreenLab 臨期百貨特定期限).

Warning logic (user-specified 2026-08-27):
  - SKU has DP value (e.g. 31) but GreenLab requires more (e.g. 60)  -> WARN (below)
  - SKU has NO DP value but GreenLab has a requirement               -> WARN (missing)
  - SKU DP >= GreenLab requirement                                   -> OK (not listed)
  - GreenLab has no requirement (— / Exclude in GL / unmatched)      -> not checked

Output: data/shelf_life_check.json (window.shelfLifeCheckData = {...}) + printed summary.
Usage:
  python check_shelf_life.py [--exports FILE1 [FILE2 ...]] [--greenlab PATH] [--out PATH]
  Default: scan ./reports/product_exports/*.xlsx (or ~/Downloads/Product_export_all_column_*.xlsx),
           ./data/GreenLab.xlsx, write data/shelf_life_check.json
"""
import argparse
import datetime
import glob
import json
import os
import re
import sys
import warnings

import openpyxl

warnings.filterwarnings('ignore')

EXPORT_GLOB_CANDIDATES = [
    'reports/product_exports/Product_export_all_column_*.xlsx',
    '~/Downloads/Product_export_all_column_*.xlsx',
    '/home/snkwok/P0068001_Product_export_all_column_merged_*.xlsx',
]
COL_SKU = 1
COL_CAT = 3          # Primary Category Code (idx 3)
COL_BRAND = 4
COL_NAME_CHI = 12    # SKU Name Chi
COL_DP = 119         # Minimum Shelf Life

NUM_RE = re.compile(r'(\d+)')


def parse_dp(val):
    """Extract days from Minimum Shelf Life cell. Accepts int, '46', '至少91日食用期', '91 Days'."""
    if val is None:
        return None
    s = str(val).strip()
    if s in ('', '—', '-', 'None', 'N/A', 'NA'):
        return None
    m = NUM_RE.search(s)
    if m:
        return int(m.group(1))
    return None


def parse_greenlab_period(val):
    """GreenLab col I: numeric string (days) / '—' / 'Exclude in GL'. Returns int or None."""
    if val is None:
        return None
    s = str(val).strip()
    if s in ('', '—', '-', 'None', 'N/A', 'Exclude in GL', 'exclude'):
        return None
    m = NUM_RE.search(s)
    if m:
        return int(m.group(1))
    return None


def find_exports(explicit):
    if explicit:
        return explicit
    for pat in EXPORT_GLOB_CANDIDATES:
        hits = sorted(glob.glob(os.path.expanduser(pat)))
        if hits:
            return hits
    return []


def load_greenlab(path):
    wb = openpyxl.load_workbook(path, read_only=True)
    ws = wb['Sheet4']
    it = ws.iter_rows(values_only=True)
    next(it)
    gl = {}
    for r in it:
        if r[4] is None:
            continue
        gl[str(r[4]).strip()] = (r[8], r[5], r[6])  # period, name_chi, name_en
    wb.close()
    return gl


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--exports', nargs='+', default=None)
    ap.add_argument('--greenlab', default='/home/snkwok/P0068001-Store-Dashboard/data/GreenLab.xlsx')
    ap.add_argument('--out', default='/home/snkwok/P0068001-Store-Dashboard/data/shelf_life_check.json')
    a = ap.parse_args()

    gl = load_greenlab(a.greenlab)
    print(f'GreenLab mapping: {len(gl)} categories')

    export_files = find_exports(a.exports)
    if not export_files:
        print('ERROR: no export files found')
        sys.exit(1)
    print(f'Export files: {len(export_files)}')

    total = 0
    checked = 0
    warnings_list = []
    seen = set()
    for f in export_files:
        wb = openpyxl.load_workbook(f, read_only=True)
        ws = wb['Product Template']
        it = ws.iter_rows(values_only=True)
        hdr = next(it)
        if len(hdr) <= COL_DP or hdr[COL_DP] != 'Minimum Shelf Life':
            print(f'  SKIP {f}: DP col mismatch ({hdr[COL_DP] if len(hdr) > COL_DP else "short"})')
            wb.close()
            continue
        n = 0
        for r in it:
            if r[COL_SKU] is None:
                continue
            sku = str(r[COL_SKU]).strip()
            if sku in seen:
                continue
            seen.add(sku)
            n += 1
            total += 1
            cat_raw = str(r[COL_CAT]).strip() if r[COL_CAT] is not None else ''
            # Primary category = first code if multiple
            cat = cat_raw.split(',')[0].strip() if cat_raw else ''
            dp = parse_dp(r[COL_DP] if len(r) > COL_DP else None)
            gl_period = parse_greenlab_period(gl.get(cat, (None,))[0]) if cat else None
            if gl_period is None:
                continue  # GreenLab no requirement -> not checked
            checked += 1
            if dp is None:
                warnings_list.append({
                    'sku': sku,
                    'name': str(r[COL_NAME_CHI]).strip() if len(r) > COL_NAME_CHI and r[COL_NAME_CHI] else '',
                    'brand': str(r[COL_BRAND]).strip() if len(r) > COL_BRAND and r[COL_BRAND] else '',
                    'category_code': cat,
                    'dp': '',
                    'greenlab_required': gl_period,
                    'status': 'missing',
                })
            elif dp < gl_period:
                warnings_list.append({
                    'sku': sku,
                    'name': str(r[COL_NAME_CHI]).strip() if len(r) > COL_NAME_CHI and r[COL_NAME_CHI] else '',
                    'brand': str(r[COL_BRAND]).strip() if len(r) > COL_BRAND and r[COL_BRAND] else '',
                    'category_code': cat,
                    'dp': dp,
                    'greenlab_required': gl_period,
                    'status': 'below',
                })
        print(f'  {os.path.basename(f)}: {n} rows')
        wb.close()

    warnings_list.sort(key=lambda w: (w['status'], w['greenlab_required'], w['sku']))
    payload = {
        'generated_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
        'source_export': os.path.basename(export_files[0]) if export_files else '',
        'total_skus': total,
        'checked_skus': checked,
        'warning_count': len(warnings_list),
        'warnings': warnings_list,
    }
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print(f'Total SKUs: {total} | checked: {checked} | warnings: {len(warnings_list)}')
    print(f'  missing: {sum(1 for w in warnings_list if w["status"] == "missing")} | below: {sum(1 for w in warnings_list if w["status"] == "below")}')
    print('SAVED:', a.out)


if __name__ == '__main__':
    main()
