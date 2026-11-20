"""Lab 8: real SQLite transactions, HTTP contracts and query scaling."""
from copy import deepcopy
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, text
from sqlmodel import Session
from labs.lab_1_2.database.db import make_engine
from labs.lab_1_2.database.models import CargoItem
from labs.lab_1_2.main import create_app
from labs.lab_1_2.seed import seed_demo
from labs.lab_1_2.test_crud import payload
from tools.measure_lab_queries import measure


@pytest.fixture
def database_api():
    engine=make_engine(':memory:');seed_demo(engine)
    try:
        with TestClient(create_app(engine)) as client:
            yield engine,client
    finally:
        engine.dispose()


def test_full_crud_with_put_and_persistent_identity(database_api):
    engine,client=database_api
    created=client.post('/api/orders',json=payload())
    assert created.status_code==201
    initial=created.json();path=created.headers['Location']
    data=payload();data.pop('notes');data['items'][0]['weight_kg']='20.00'
    changed=client.put(path,json=data)
    assert changed.status_code==200
    body=changed.json()
    assert body['id']==initial['id'] and body['number']==initial['number']
    assert body['created_at']==initial['created_at'] and body['status']=='New'
    assert body['notes'] is None and body['quoted_amount']=='165300.00'
    with Session(engine) as session:
        assert session.exec(text('SELECT Notes FROM Orders WHERE OrderID=:id').bindparams(id=body['id'])).scalar() is None
        assert session.exec(text('SELECT WeightKg FROM CargoItems WHERE OrderID=:id').bindparams(id=body['id'])).scalar()==20
    assert client.delete(path).status_code==204
    assert client.get(path).status_code==404
    with Session(engine) as session:
        assert session.exec(text('SELECT COUNT(*) FROM CargoItems WHERE OrderID=:id').bindparams(id=body['id'])).scalar()==0


def test_put_requires_all_input_fields(lab_client):
    assert lab_client.put('/api/orders/1',json={'notes':'partial'}).status_code==422


def test_malformed_json_is_400_and_does_not_echo_input(lab_client):
    marker='sensitive-input-marker'
    response=lab_client.post('/api/orders',content='{"Password":"'+marker+'",',headers={'Content-Type':'application/json'})
    assert response.status_code==400
    assert marker not in response.text and 'input' not in response.json()['detail'][0]


@pytest.mark.parametrize('body',[{},None,{'client_id':999999}])
def test_empty_or_incomplete_body_does_not_change_database(lab_client,body):
    before=lab_client.get('/api/summary').json()
    assert lab_client.post('/api/orders',json=body).status_code==422
    assert lab_client.get('/api/summary').json()==before


def test_nonexistent_client_reference_is_rejected(lab_client):
    data=payload();data['client_id']=999999
    response=lab_client.post('/api/orders',json=data)
    assert response.status_code==422 and 'client_id' in response.text


def test_sql_injection_like_search_is_literal(lab_client):
    before=lab_client.get('/api/summary').json()
    assert lab_client.get('/api/orders',params={'search':"' OR 1=1 --"}).json()==[]
    assert lab_client.get('/api/summary').json()==before


def test_error_response_and_logs_do_not_contain_extra_secret(lab_client,caplog):
    marker='private-marker-7363'
    body=payload();body['Password']=marker
    response=lab_client.post('/api/orders',json=body)
    assert response.status_code==422
    assert marker not in response.text and marker not in caplog.text


def test_create_transaction_rolls_back_after_database_failure(database_api):
    engine,client=database_api
    before=client.get('/api/summary').json()
    def null_required_field(mapper,connection,target): target.Description=None
    event.listen(CargoItem,'before_insert',null_required_field)
    try:
        response=client.post('/api/orders',json=payload())
    finally:
        event.remove(CargoItem,'before_insert',null_required_field)
    assert response.status_code==409
    assert 'INSERT' not in response.text and 'NOT NULL' not in response.text
    assert client.get('/api/summary').json()==before
    assert client.post('/api/orders',json=payload()).status_code==201


def test_replace_transaction_restores_old_items_after_failure(database_api):
    engine,client=database_api
    original=client.get('/api/orders/1').json()
    def null_required_field(mapper,connection,target): target.Description=None
    event.listen(CargoItem,'before_insert',null_required_field)
    try:
        response=client.put('/api/orders/1',json=payload())
    finally:
        event.remove(CargoItem,'before_insert',null_required_field)
    assert response.status_code==409
    assert client.get('/api/orders/1').json()==original
    with Session(engine) as session:
        assert session.exec(text('PRAGMA integrity_check')).scalar()=='ok'
        assert session.exec(text('PRAGMA foreign_key_check')).all()==[]


def test_list_query_count_does_not_grow_with_orders():
    result=measure()
    assert result['3']['orders']==3 and result['30']['orders']==30
    assert result['30']['selects']==result['3']['selects']<=4


@pytest.mark.parametrize('weight,expected',[('0.01','165000.15'),('10.00','165150.00')])
def test_price_boundaries_from_real_api(lab_client,weight,expected):
    body=payload();body['items'][0]['weight_kg']=weight
    response=lab_client.post('/api/orders',json=body)
    assert response.status_code==201 and response.json()['quoted_amount']==expected


def test_zero_weight_rejected(lab_client):
    body=payload();body['items'][0]['weight_kg']='0.00'
    assert lab_client.post('/api/orders',json=body).status_code==422
