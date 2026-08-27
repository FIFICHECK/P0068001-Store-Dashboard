#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P0068001 MMS Minimum Shelf Life updater.

Flow per SKU (verified 2026-08-27 with SKU 4550583916213 -> 91 SUCCESS):
  1. POST /product/v2/products {page,size,skuId,buCode,disableInventory,orderBy,storeId} -> product uuid
  2. Build minimal edit payload with minimum_shelf_life = suggested value
  3. POST /product/single/edit {uuid, sku_id, product_id, minimum_shelf_life, ...} -> recordId
  4. GET /product/checkSaveProductRecordsStatus?recordIds=<id> -> poll until SUCCESS/FAIL

Auth: Bearer <accessToken> from MMS login (webLogin response).

Usage:
  python update_shelf_life_mms.py --token <jwt> --sku P0068001_S_4550583916213 --value 91
  python update_shelf_life_mms.py --token <jwt> --json data/pending_updates.json   # batch from file
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


def call(method, path, token, body=None):
    cmd = ['curl', '-s', '-X', method, BASE + path]
    cmd += HDR + ['-H', f'Authorization: Bearer {token}']
    if body is not None:
        cmd += ['-d', json.dumps(body)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    try:
        return json.loads(r.stdout)
    except Exception:
        return {'raw': r.stdout[:300], 'status_code': r.returncode}


def find_product(token, sku_id):
    """Search product by SKU id (no store prefix) -> product dict."""
    body = {'page': 1, 'size': 20, 'skuId': sku_id, 'buCode': ['HKTV'],
            'disableInventory': True, 'orderBy': ['modified_time desc'],
            'storeId': [STORE_ID], 'forceOffline': None}
    j = call('POST', '/product/v2/products', token, body)
    if j.get('status') != 1 or not j.get('data', {}).get('products'):
        return None, j
    return j['data']['products'][0], j


def build_payload(product, new_value):
    """Build minimal /product/single/edit payload from the fetched product."""
    hktv = (product.get('additional') or {}).get('hktv') or {}
    p = {
        'uuid': product.get('uuid'),
        'sku_id': product.get('sku_id'),
        'product_id': product.get('product_id'),
        'minimum_shelf_life': new_value,
        'bu': 'HKTV',
        'storeId': hktv.get('store_id'),
        'storefrontStoreCode': hktv.get('storefront_store_code'),
        'store_sku_id': hktv.get('store_sku_id'),
        'merchant_id': product.get('merchant_id'),
        'brand_id': product.get('brand_id'),
        'product_type_code': hktv.get('product_type_code'),
        'primary_category_code': hktv.get('primary_category_code'),
        'status': hktv.get('status'),
    }
    return {k: v for k, v in p.items() if v is not None}


def update_one(token, sku, value):
    """Update one SKU. sku may be P0068001_S_xxx or bare xxx."""
    sku_id = sku.split('_S_')[-1] if '_S_' in sku else sku
    prod, j = find_product(token, sku_id)
    if prod is None:
        return {'sku': sku, 'ok': False, 'step': 'find', 'error': json.dumps(j, ensure_ascii=False)[:200]}
    payload = build_payload(prod, value)
    j = call('POST', '/product/single/edit', token, payload)
    if j.get('status') != 1 or not j.get('data', {}).get('recordId'):
        return {'sku': sku, 'ok': False, 'step': 'edit', 'error': json.dumps(j, ensure_ascii=False)[:300]}
    rid = j['data']['recordId']
    # poll status
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
    ap.add_argument('--json', default=None, help='JSON file: [{"sku": "...", "value": 91}, ...]')
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
        status = '✅' if r['ok'] else '❌'
        print(f'{status} {r.get("sku")} -> {r.get("value")} {r.get("error", "")}')
        time.sleep(1)

    ok = sum(1 for r in results if r['ok'])
    print(f'\nDone: {ok}/{len(results)} succeeded')
    with open('/tmp/shelf_life_update_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    print('Results saved: /tmp/shelf_life_update_results.json')
    sys.exit(0 if ok == len(results) else 1)


if __name__ == '__main__':
    main()
