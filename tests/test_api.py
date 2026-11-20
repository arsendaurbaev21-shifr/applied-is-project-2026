"""Lab 7: pytest integration checks against an isolated FastAPI/SQLite app."""
from labs.lab_1_2.test_crud import payload


def test_get_orders_returns_list(lab_client):
    response = lab_client.get('/api/orders')
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 3


def test_post_creates_order_and_returns_201(lab_client):
    response = lab_client.post('/api/orders', json=payload())
    assert response.status_code == 201
    body = response.json()
    assert body['quoted_amount'] == '165150.00'
    assert body['items'][0]['description'] == 'Қапталған жүк'
    assert lab_client.get(response.headers['Location']).json() == body


def test_catalogs_supply_valid_form_choices(lab_client):
    response = lab_client.get('/api/catalogs')
    assert response.status_code == 200
    catalogs = response.json()
    assert set(catalogs) == {'clients', 'routes', 'tariffs', 'cargo_types'}
    assert all(len(rows) == 3 for rows in catalogs.values())
    data = payload()
    data.update(client_id=catalogs['clients'][1]['id'], route_id=catalogs['routes'][1]['id'],
                tariff_id=catalogs['tariffs'][1]['id'])
    data['items'][0]['cargo_type_id'] = catalogs['cargo_types'][1]['id']
    assert lab_client.post('/api/orders', json=data).status_code == 201


def test_invalid_post_does_not_change_summary(lab_client):
    before = lab_client.get('/api/summary').json()
    data = payload()
    data['items'][0]['weight_kg'] = '-1'
    assert lab_client.post('/api/orders', json=data).status_code == 422
    assert lab_client.get('/api/summary').json() == before


def test_health_and_final_openapi(lab_client):
    assert lab_client.get('/health').json() == {'status': 'ok'}
    assert lab_client.get('/').json()['labs'] == list(range(1, 9))
    assert lab_client.get('/docs').status_code == 200
    paths = lab_client.get('/openapi.json').json()['paths']
    assert {'get', 'post'} <= paths['/api/orders'].keys()
    assert {'get', 'put', 'patch', 'delete'} <= paths['/api/orders/{order_id}'].keys()
    assert '/api/catalogs' in paths
