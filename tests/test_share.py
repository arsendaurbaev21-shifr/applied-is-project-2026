import secrets
import pytest
from backend.share import create_share_app

HOST='qazcargo-test-example.trycloudflare.com'
ORIGIN='https://'+HOST


@pytest.mark.parametrize('hostname',['evil.example','*','.trycloudflare.com','https://'+HOST,HOST+':443'])
def test_share_rejects_unissued_hostname_shapes(hostname):
    with pytest.raises(ValueError):create_share_app(hostname)


def test_public_host_cookie_csrf_and_forwarding_headers():
    app=create_share_app(HOST)
    client=app.test_client()
    first=client.get('/api/auth/session',base_url=ORIGIN)
    cookie=first.headers['Set-Cookie']
    assert 'Secure' in cookie and 'HttpOnly' in cookie and 'SameSite=Lax' in cookie
    assert client.get('/',base_url='https://evil.example').status_code==400
    csrf=first.json['csrf']
    assert client.post('/api/auth/logout',base_url=ORIGIN,headers={'Origin':'https://evil.example','X-CSRF-Token':csrf}).status_code==403
    assert client.post('/api/auth/logout',base_url=ORIGIN,headers={'Origin':'https://evil.example','X-Forwarded-Host':'evil.example','X-CSRF-Token':csrf}).status_code==403
    assert client.post('/api/auth/logout',base_url=ORIGIN,headers={'Origin':ORIGIN}).status_code==403
    assert client.post('/api/auth/logout',base_url=ORIGIN,headers={'Origin':ORIGIN,'X-CSRF-Token':csrf}).status_code==200


def test_public_registration_and_login_use_real_sql(test_database):
    app=create_share_app(HOST)
    client=app.test_client()
    csrf=client.get('/api/auth/session',base_url=ORIGIN).json['csrf']
    email='share-'+secrets.token_hex(5)+'@test.invalid'
    password=secrets.token_urlsafe(20)
    registration=client.post('/api/auth/register',base_url=ORIGIN,headers={'Origin':ORIGIN,'X-CSRF-Token':csrf},
        json={'FullName':'Уақытша сілтеме сынағы','Email':email,'Password':password,'Phone':'TEST'})
    assert registration.status_code==201,registration.json
    assert registration.json['user']['Role']=='client'
    assert client.get('/customer',base_url=ORIGIN).status_code==200
    assert client.post('/api/auth/logout',base_url=ORIGIN,headers={'Origin':ORIGIN,'X-CSRF-Token':registration.json['csrf']}).status_code==200
    csrf=client.get('/api/auth/session',base_url=ORIGIN).json['csrf']
    login=client.post('/api/auth/login',base_url=ORIGIN,headers={'Origin':ORIGIN,'X-CSRF-Token':csrf},json={'Email':email,'Password':password})
    assert login.status_code==200,login.json
    assert client.get('/api/auth/users',base_url=ORIGIN).status_code==403
