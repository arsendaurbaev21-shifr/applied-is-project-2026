"""Integration tests create and drop ONLY a uniquely named disposable SQL database."""
import os
import re
import secrets
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture(scope='session')
def test_database():
    from dotenv import load_dotenv
    from backend.db import connect
    from backend.install import consume
    load_dotenv(ROOT / '.env')
    name='QazCargo_Test_'+secrets.token_hex(6)
    original=os.environ.get('DB_DATABASE','QazCargo')
    conn=connect('master',True)
    created=False
    try:
        assert conn.cursor().execute('SELECT DB_ID(?)',(name,)).fetchone()[0] is None
        for filename in ['01_create_database.sql','02_seed_catalogs.sql','04_delivery_tracking_notifications.sql','05_order_drafts.sql','06_city_network.sql']:
            script=(ROOT/'database'/filename).read_text(encoding='utf-8-sig')
            script=script.replace("DB_ID(N'QazCargo')",f"DB_ID(N'{name}')").replace('CREATE DATABASE QazCargo',f'CREATE DATABASE [{name}]').replace('USE QazCargo;',f'USE [{name}];')
            for batch in re.split(r'^\s*GO\s*(?:--[^\n]*)?$',script,flags=re.M|re.I):
                if batch.strip():
                    cur=conn.cursor();cur.execute(batch);consume(cur);cur.close()
                    if conn.cursor().execute('SELECT DB_ID(?)',(name,)).fetchone()[0]:created=True
        os.environ['DB_DATABASE']=name
        yield name
    finally:
        os.environ['DB_DATABASE']=original
        conn.close()
        if created:
            assert re.fullmatch(r'QazCargo_Test_[0-9a-f]{12}',name)
            cleanup=connect('master',True)
            try:
                cur=cleanup.cursor();cur.execute(f'ALTER DATABASE [{name}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE');consume(cur)
                cur.execute(f'DROP DATABASE [{name}]');consume(cur);cur.close()
            finally:cleanup.close()


class Actor:
    def __init__(self,app):self.client=app.test_client();self.token=self.client.get('/api/auth/session').json['csrf'];self.user=None
    def request(self,method,path,body=None,**kwargs):
        headers={'X-CSRF-Token':self.token,**kwargs.pop('headers',{})}
        response=self.client.open('/api'+path,method=method,json=body,headers=headers,**kwargs)
        if response.is_json and response.json.get('csrf'):self.token=response.json['csrf']
        if response.is_json and response.json.get('user'):self.user=response.json['user']
        return response
    def get(self,path):return self.request('GET',path)
    def post(self,path,body=None,**kw):return self.request('POST',path,body,**kw)


@pytest.fixture
def app(test_database):
    from backend.app import create_app
    return create_app({'TESTING':True})


@pytest.fixture
def actors(app):
    from werkzeug.security import generate_password_hash
    from backend.db import transaction
    secret=secrets.token_urlsafe(18)
    mail='admin-'+secrets.token_hex(5)+'@test.invalid'
    with transaction(True) as q:
        q.insert('Users','UserID',dict(Email=mail,FullName='SQL test admin',PasswordHash=generate_password_hash(secret,method='scrypt'),Role='admin',ClientID=None))
    admin=Actor(app);assert admin.post('/auth/login',{'Email':mail,'Password':secret}).status_code==200
    clients=[]
    for index in range(2):
        client=Actor(app);email='client-'+secrets.token_hex(5)+'@test.invalid'
        response=client.post('/auth/register',{'FullName':'Тест клиент '+str(index),'Phone':'TEST','Email':email,'Password':secret})
        assert response.status_code==201,response.json
        client.credentials={'Email':email,'Password':secret};clients.append(client)
    admin.credentials={'Email':mail,'Password':secret}
    return admin,*clients


def order_data(**overrides):
    return {'RouteID':1,'TariffID':1,'PickupDate':'2026-11-20',
            'SenderName':'Тест жіберуші','SenderPhone':'+77010000000','PickupAddress':'Тест көшесі, 10',
            'RecipientName':'Тест алушы','RecipientPhone':'+77020000000','DeliveryAddress':'Тест көшесі, 20',
            'PickupWindowStart':'09:00','PickupWindowEnd':'18:00',
            'items':[{'CargoTypeID':1,'Description':'Оқу жүгі','WeightKg':'100.25','VolumeM3':'1.125','Quantity':4}],**overrides}


def new_order(client,**overrides):
    response=client.post('/orders',order_data(**overrides));assert response.status_code==201,response.json
    return response.json['id']


@pytest.fixture
def lab_client():
    from fastapi.testclient import TestClient
    from labs.lab_1_2.database.db import make_engine
    from labs.lab_1_2.main import create_app
    from labs.lab_1_2.seed import seed_demo
    engine = make_engine(':memory:')
    seed_demo(engine)
    try:
        with TestClient(create_app(engine)) as client:
            yield client
    finally:
        engine.dispose()


@pytest.fixture
def ui_backend(lab_client, monkeypatch):
    """Exercise real API/database behavior from Streamlit without a TCP port."""
    import requests
    from labs.lab_1_2 import ui_client

    def send(method, url, *, params=None, json=None, timeout=None):
        from urllib.parse import urlsplit
        response = lab_client.request(method, urlsplit(url).path, params=params, json=json)
        result = requests.Response()
        result.status_code = response.status_code
        result._content = response.content
        result.headers.update(response.headers)
        result.url = url
        return result

    monkeypatch.setattr(ui_client.requests, 'request', send)
    return lab_client
