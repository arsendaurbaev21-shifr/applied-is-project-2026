"""Run explicitly: real Flask + disposable SQL Server database, never production rows."""
import secrets
import pytest
from conftest import Actor


@pytest.mark.parametrize('value',['','short','password123','1111111111'])
def test_registration_rejects_weak_password(app,value):
    actor=Actor(app)
    response=actor.post('/auth/register',{'FullName':'Lab 8','Email':'lab8-'+secrets.token_hex(5)+'@test.invalid',
                       'Phone':'TEST','Password':value})
    assert response.status_code==400
    assert response.json['error']['field']=='Password'


def test_unknown_login_and_empty_password_are_denied(app):
    actor=Actor(app)
    response=actor.post('/auth/login',{'Email':'unknown-'+secrets.token_hex(6)+'@test.invalid','Password':''})
    assert response.status_code==401 and response.json['error']['code']=='login_failed'


def test_unauthenticated_admin_resource(app):
    assert Actor(app).get('/auth/users').status_code==401


def test_regular_user_cannot_use_admin_resource(actors):
    admin,client,_=actors
    assert client.get('/auth/users').status_code==403
    assert admin.get('/auth/users').status_code==200


def test_malformed_json_and_missing_csrf_are_denied(app):
    actor=Actor(app)
    response=actor.client.post('/api/auth/login',data='{broken',content_type='application/json',
                               headers={'X-CSRF-Token':actor.token})
    assert response.status_code==400
    assert actor.client.post('/api/auth/login',json={}).status_code==403


def test_revoked_session_is_denied(actors):
    admin,client,_=actors
    uid=client.user['UserID']
    assert admin.request('PATCH',f'/auth/users/{uid}',{'IsActive':False}).status_code==200
    assert client.get('/orders').status_code==401


def test_password_not_returned_or_logged(app,caplog):
    actor=Actor(app);marker=secrets.token_urlsafe(20)
    response=actor.post('/auth/login',{'Email':'lab8-absent@test.invalid','Password':marker})
    assert response.status_code==401
    assert marker not in response.get_data(as_text=True) and marker not in caplog.text
    assert 'PasswordHash' not in response.get_data(as_text=True)
