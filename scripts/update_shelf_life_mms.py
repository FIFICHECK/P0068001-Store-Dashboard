#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P0068001 MMS Minimum Shelf Life updater v3 — VERIFIED payload structure.

Verified 2026-08-27:
  - UI save = POST /product/single/edit with body {"product": {snake_case dict}}
  - The product dict == /product/v2/products product dict (32 keys incl. additional.hktv),
    with minimum_shelf_life overridden
  - Success example: SKU 4550583916213 -> 91 (SUCCESS, recordId 109500498)
  - Poll: GET /product/checkSaveProductRecordsStatus?recordIds=<id> until SUCCESS

Usage:
  python update_shelf_life_mms.py --token <jwt> --sku P0068001_S_4550583916213 --value 91
  python update_shelf_life_mms.py --token <jwt> --json pending.json
  (pending.json: {"updates": [{"sku": "...", "value": 91}, ...]})
"""
import argparse
import base64
import json
import subprocess
import sys
import time

BASE = 'https://merchant-web.shoalter.com'
STORE_ID = 33249

HDR = ['-H', 'Content-Type: application/json',
       '-H', 'Accept: application/json',
       '-H', 'Origin: https://merchant.shoalter.com',
       '-H', 'Referer: https://merchant.shoalter.com/']

KEEP = ['uuid', 'colour_families', 'color', 'size_system', 'size', 'option1', 'option2',
        'option3', 'option1_value', 'option2_value', 'option3_value', 'barcodes',
        'carton_size', 'weight_unit', 'weight', 'brand_id', 'merchant_id', 'sku_id',
        'manufactured_country', 'packing_dimension_unit', 'packing_height', 'packing_length',
        'packing_depth', 'packing_box_type', 'original_price', 'product_id',
        'minimum_shelf_life', 'merchant_name', 'sku_name_en', 'sku_name_ch', 'sku_name_sc',
        'additional']


def call(method, path, token, body=None):
    cmd = ['curl', '-s', '-X', method, BASE + path]
    cmd += HDR + ['-H', f'Authorization: Bearer {token}']
    if body is not None:
        cmd += ['-d', json.dumps(body)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    try:
        return json.loads(r.stdout)
    except Exception:
        return {'raw': r.stdout[:300], 'code': r.returncode}


def find_product(token, sku_id):
    body = {'page': 1, 'size': 20, 'skuId': sku_id, 'buCode': ['HKTV'],
            'disableInventory': True, 'orderBy': ['modified_time desc'],
            'storeId': [STORE_ID], 'forceOffline': None}
    j = call('POST', '/product/v2/products', token, body)
    if j.get('status') != 1 or not j.get('data', {}).get('products'):
        return None, j
    return j['data']['products'][0], j


def build_edit_payload(product, new_value):
    payload = {}
    for k in KEEP:
        if k in product:
            payload[k] = product[k]
    # Filter additional.hktv to the exact keys the UI edit form submits (53 keys) —
    # extra keys from the v2 API (warehouse_code:None, force_offline, status, ...)
    # break the server validation.
    UI_HKTV_KEYS = ['stores', 'product_ready_method', 'delivery_method', 'product_type_code',
                    'primary_category_code', 'visibility', 'currency', 'cost_record', 'style',
                    'warranty', 'contract_no', 'is_primary_sku', 'sku_short_description_en',
                    'sku_short_description_ch', 'sku_short_description_sc', 'selling_price',
                    'discount_text_en', 'discount_text_ch', 'discount_text_sc', 'mall_dollar',
                    'vip_mall_dollar', 'user_max', 'main_photo', 'variant_product_photo',
                    'warehouse_id', 'packing_spec_en', 'packing_spec_ch', 'packing_spec_sc',
                    'invoice_remarks_en', 'invoice_remarks_ch', 'invoice_remarks_sc', 'return_days',
                    'product_ready_days', 'pickup_days', 'pickup_timeslot', 'goods_type',
                    'warranty_period_unit', 'warranty_period', 'warranty_supplier_en',
                    'warranty_supplier_ch', 'warranty_supplier_sc', 'service_centre_address_en',
                    'service_centre_address_ch', 'service_centre_address_sc',
                    'service_centre_email', 'service_centre_contact', 'warranty_remark_en',
                    'warranty_remark_ch', 'warranty_remark_sc', 'online_status', 'storage_type',
                    'store_id', 'delivery_district']
    add = payload.get('additional') or {}
    hktv = add.get('hktv') or {}
    add['hktv'] = {k: hktv[k] for k in UI_HKTV_KEYS if k in hktv}
    payload['additional'] = add
    payload['minimum_shelf_life'] = new_value
    return {'product': payload}


def update_one(token, sku, value):
    sku_id = sku.split('_S_')[-1] if '_S_' in sku else sku
    prod, j = find_product(token, sku_id)
    if prod is None:
        return {'sku': sku, 'ok': False, 'step': 'find', 'error': json.dumps(j, ensure_ascii=False)[:200]}
    payload = build_edit_payload(prod, value)
    j = call('POST', '/product/single/edit', token, payload)
    if j.get('status') != 1 or not j.get('data', {}).get('recordId'):
        return {'sku': sku, 'ok': False, 'step': 'edit', 'error': json.dumps(j, ensure_ascii=False)[:300]}
    rid = j['data']['recordId']
    for _ in range(6):
        time.sleep(2)
        st = call('GET', f'/product/checkSaveProductRecordsStatus?recordIds={rid}', token)
        rows = (st.get('data') or [{}])[0].get('rows') or []
        if rows and rows[0].get('status') == 'SUCCESS':
            return {'sku': sku, 'ok': True, 'recordId': rid, 'value': value}
        if rows and rows[0].get('status') not in ('UPDATING', 'SUCCESS'):
            return {'sku': sku, 'ok': False, 'step': 'status', 'error': json.dumps(rows[0], ensure_ascii=False)[:200]}
    return {'sku': sku, 'ok': False, 'step': 'timeout', 'recordId': rid}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--token', required=True)
    ap.add_argument('--sku', default=None)
    ap.add_argument('--value', type=int, default=None)
    ap.add_argument('--json', default=None)
    a = ap.parse_args()

    token = a.token
    if token.startswith('b64:'):
        token = base64.b64decode(token[4:]).decode()

    jobs = []
    if a.json:
        jobs = json.load(open(a.json, encoding='utf-8'))
        if isinstance(jobs, dict) and 'updates' in jobs:
            jobs = jobs['updates']
    elif a.sku and a.value:
        jobs = [{'sku': a.sku, 'value': a.value}]
    else:
        print('ERROR: need --sku --value OR --json')
        sys.exit(1)

    print(f'Updating {len(jobs)} SKU(s)...')
    results = []
    for j in jobs:
        r = update_one(token, j['sku'], j.get('value', j.get('suggested')))
        results.append(r)
        status = 'OK' if r['ok'] else 'FAIL'
        print(f'{status} {r.get("sku")} -> {r.get("value")} {r.get("error", "")}')
        time.sleep(2)

    ok = sum(1 for r in results if r['ok'])
    print(f'\nDone: {ok}/{len(results)} succeeded')
    with open('/tmp/shelf_life_update_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    print('Results saved: /tmp/shelf_life_update_results.json')
    sys.exit(0 if ok == len(results) else 1)


if __name__ == '__main__':
    main()
