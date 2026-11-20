import requests
import pytest
from labs.lab_1_2.ui_client import ApiClient, ApiError


def test_client_uses_real_api_for_json_and_204(ui_backend):
    from labs.lab_1_2.test_crud import payload
    api = ApiClient('http://backend:8000/')
    created = api.request('POST', '/api/orders', json=payload())
    found = api.request('GET', '/api/orders', params={'search': created['number']})
    assert [row['id'] for row in found] == [created['id']]
    assert api.request('DELETE', f"/api/orders/{created['id']}") is None


def test_validation_message_names_bad_field(ui_backend):
    from labs.lab_1_2.test_crud import payload
    data = payload()
    data['items'][0]['weight_kg'] = '-10'
    with pytest.raises(ApiError, match=r'items\.0\.weight_kg'):
        ApiClient().request('POST', '/api/orders', json=data)


def test_connection_failure_does_not_retry_writes(monkeypatch):
    calls = []
    def timeout(*args, **kwargs):
        calls.append((args, kwargs))
        raise requests.Timeout()
    monkeypatch.setattr(requests, 'request', timeout)
    with pytest.raises(ApiError, match='қайталамас бұрын'):
        ApiClient().request('POST', '/api/orders', json={'notes': 'test'})
    assert len(calls) == 1


@pytest.mark.parametrize('status,content', [(502, b'<html>secret traceback</html>'), (200, b'not json')])
def test_bad_server_response_becomes_readable_error(monkeypatch, status, content):
    response = requests.Response()
    response.status_code = status
    response._content = content
    monkeypatch.setattr(requests, 'request', lambda *a, **kw: response)
    with pytest.raises(ApiError) as raised:
        ApiClient().request('GET', '/api/orders')
    assert 'secret traceback' not in str(raised.value)


def test_backend_address_comes_from_environment(monkeypatch):
    monkeypatch.setenv('BACKEND_URL', 'http://backend:8000/')
    assert ApiClient().base_url == 'http://backend:8000'
