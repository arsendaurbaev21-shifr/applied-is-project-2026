"""Verify the disposable lab stack and persistence; never use production APIs."""
import argparse
from datetime import date, timedelta
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4


def request(base, method, path, data=None, expected=200):
    raw = json.dumps(data).encode() if data is not None else None
    req = Request(base + path, data=raw, method=method, headers={'Content-Type': 'application/json'})
    try:
        with urlopen(req, timeout=15) as response:
            status, content = response.status, response.read()
    except HTTPError as error:
        status, content = error.code, error.read()
    assert status == expected, f'{method} {path}: expected {expected}, got {status}'
    return json.loads(content) if content else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['create', 'verify'])
    parser.add_argument('--base-url', default='http://127.0.0.1:8000')
    parser.add_argument('--ui-url', default='http://127.0.0.1:8501')
    parser.add_argument('--state', type=Path, required=True)
    args = parser.parse_args()
    base = args.base_url.rstrip('/')
    assert request(base, 'GET', '/')['data'] == 'synthetic', 'Only synthetic lab data is supported'
    assert request(base, 'GET', '/health') == {'status': 'ok'}
    with urlopen(args.ui_url.rstrip('/') + '/_stcore/health', timeout=15) as response:
        assert response.read() == b'ok'
    if args.phase == 'create':
        before = request(base, 'GET', '/api/summary')['tables']
        catalogs = request(base, 'GET', '/api/catalogs')
        marker = 'container-check-' + uuid4().hex
        data = {'client_id': catalogs['clients'][0]['id'], 'route_id': catalogs['routes'][0]['id'],
                'tariff_id': next(t['id'] for t in catalogs['tariffs'] if t['active']),
                'pickup_date': (date.today() + timedelta(days=1)).isoformat(), 'notes': marker,
                'items': [{'cargo_type_id': catalogs['cargo_types'][0]['id'], 'description': marker,
                           'weight_kg': '10.00', 'volume_m3': '0.500', 'quantity': 2}]}
        created = request(base, 'POST', '/api/orders', data, 201)
        updated = request(base, 'PATCH', f"/api/orders/{created['id']}", {'notes': marker + '-patched'})
        assert updated['quoted_amount'] == created['quoted_amount']
        assert updated['items'] == created['items']
        found = request(base, 'GET', '/api/orders?search=' + created['number'] + '&min_price=0')
        assert [row['id'] for row in found] == [created['id']]
        bad = {**data, 'items': [{**data['items'][0], 'weight_kg': '-1'}]}
        request(base, 'POST', '/api/orders', bad, 422)
        args.state.parent.mkdir(parents=True, exist_ok=True)
        args.state.write_text(json.dumps({'order': updated, 'before': before}), encoding='utf-8')
        print('HTTP create / PATCH / search / validation: PASS; persistence marker saved.')
    else:
        state = json.loads(args.state.read_text(encoding='utf-8'))
        saved = state['order']
        actual = request(base, 'GET', f"/api/orders/{saved['id']}")
        assert actual == saved, 'Order changed across container recreation'
        assert saved['items'][0]['description'].startswith('container-check-')
        request(base, 'DELETE', f"/api/orders/{saved['id']}", expected=204)
        request(base, 'GET', f"/api/orders/{saved['id']}", expected=404)
        assert request(base, 'GET', '/api/summary')['tables'] == state['before']
        print('Persistence after recreation / DELETE / subsequent 404: PASS; marker removed.')


if __name__ == '__main__':
    main()
