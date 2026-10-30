import io
import secrets
import zipfile
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path
import pytest
from PIL import Image
from pypdf import PdfWriter
from backend.db import transaction,connect
from backend.install import consume
from conftest import Actor,new_order,order_data


def test_schema_and_catalogs(actors):
    admin,client,_=actors
    assert client.get('/health').json['tables']==19
    with transaction() as q:
        assert q.scalar('SELECT COUNT(*) FROM sys.foreign_keys')==25
        assert q.scalar("SELECT COUNT(*) FROM sys.indexes WHERE name='UX_Users_Client' AND has_filter=1")==1
    response=admin.post('/catalogs/Cities',{'Name':'Сынақ '+secrets.token_hex(3)});assert response.status_code==200
    rid=admin.post('/catalogs/Routes',{'FromCityID':1,'ToCityID':response.json['id'],'DistanceKm':'100.00'})
    assert rid.status_code==200
    assert any(r['RouteID']==rid.json['id'] for r in client.get('/public/catalogs').json['data']['Routes'])


def test_register_cannot_elevate_and_csrf(app,actors):
    raw=app.test_client()
    assert raw.post('/api/auth/register',json={}).status_code==403
    actor=Actor(app)
    assert actor.post('/auth/register',{'Role':'admin'}).status_code==400
    _,client,_=actors
    assert client.get('/catalogs').status_code==403
    assert client.post('/catalogs/Cities',{'Name':'Bad'}).status_code==403
    assert client.post('/auth/logout',headers={'Origin':'https://attacker.invalid'}).status_code==403


def test_order_price_history_and_ownership(actors):
    admin,client,other=actors;oid=new_order(client)
    detail=client.get('/orders/'+str(oid)).json
    assert detail['order']['QuotedAmount']=='196503.75'
    assert detail['order']['TotalWeightKg']=='100.25' # not multiplied by 4 packages
    assert [h['NewStatus'] for h in detail['history']]==['New']
    assert other.get('/orders/'+str(oid)).status_code==404
    assert other.post(f'/orders/{oid}/status',{'Status':'Cancelled'}).status_code==404
    assert client.post('/orders',{**order_data(),'ClientID':other.user['ClientID']}).status_code==400
    assert admin.post(f'/orders/{oid}/status',{'Status':'Confirmed'}).status_code==200
    assert client.get(f'/orders/{oid}').json['order']['Status']=='Confirmed'
    assert len(client.get(f'/orders/{oid}').json['history'])==2
    assert client.post(f'/orders/{oid}/status',{'Status':'Cancelled'}).status_code==403


def test_multi_step_rollback(actors):
    _,client,_=actors
    with transaction() as q:before=q.scalar('SELECT COUNT(*) FROM dbo.Orders WHERE ClientID=?',(client.user['ClientID'],))
    data=order_data();data['items'].append({**data['items'][0],'CargoTypeID':2147483647})
    assert client.post('/orders',data).status_code==409
    with transaction() as q:
        assert q.scalar('SELECT COUNT(*) FROM dbo.Orders WHERE ClientID=?',(client.user['ClientID'],))==before
        assert q.scalar('SELECT COUNT(*) FROM dbo.CargoItems c JOIN dbo.Orders o ON o.OrderID=c.OrderID WHERE o.ClientID=?',(client.user['ClientID'],))==0


def test_payments_balance_overpayment_and_cancel(actors):
    admin,client,other=actors;oid=new_order(client)
    assert admin.post(f'/orders/{oid}/payments',{'Amount':'1000','Method':'Transfer'}).status_code==200
    detail=client.get(f'/orders/{oid}').json
    assert detail['order']['PaidAmount']=='1000.00' and detail['order']['BalanceAmount']=='195503.75'
    assert admin.post(f'/orders/{oid}/payments',{'Amount':'195503.76','Method':'Cash'}).status_code==409
    assert admin.post(f'/orders/{oid}/status',{'Status':'Cancelled'}).status_code==409
    assert client.post(f'/orders/{oid}/payments',{'Amount':1,'Method':'Cash'}).status_code==403
    assert other.get('/reports/payments').json['rows']==[]
    assert admin.post(f'/orders/{oid}/cargo',order_data()['items'][0]).status_code==409


def test_concurrent_payments_cannot_overpay(app,actors):
    admin,client,_=actors;oid=new_order(client)
    def pay(_):
        actor=Actor(app);assert actor.post('/auth/login',admin.credentials).status_code==200
        return actor.post(f'/orders/{oid}/payments',{'Amount':'150000','Method':'Cash'}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:statuses=list(pool.map(pay,range(2)))
    assert sorted(statuses)==[200,409],statuses
    assert client.get(f'/orders/{oid}').json['order']['PaidAmount']=='150000.00'


def trip_data(day='2026-11-20',**kw):return {'VehicleID':1,'DriverID':1,'DepartureAt':day+'T00:30','ArrivalAt':day+'T12:00',**kw}


def test_trip_timezone_capacity_overlap_and_status(actors):
    admin,client,_=actors;oid=new_order(client)
    assert admin.post(f'/orders/{oid}/status',{'Status':'Confirmed'}).status_code==200
    assert admin.request('PUT',f'/orders/{oid}/trip',trip_data(VehicleID=3)).status_code==409
    response=admin.request('PUT',f'/orders/{oid}/trip',trip_data());assert response.status_code==200,response.json
    detail=client.get(f'/orders/{oid}').json
    assert detail['trip']['DepartureAt']=='2026-11-19T19:30:00+00:00' # local midnight stays on pickup date
    second=new_order(client);admin.post(f'/orders/{second}/status',{'Status':'Confirmed'})
    assert admin.request('PUT',f'/orders/{second}/trip',trip_data()).status_code==409
    assert admin.post(f'/orders/{oid}/status',{'Status':'InTransit'}).status_code==200
    assert client.get(f'/orders/{oid}').json['trip']['Status']=='InTransit'
    assert admin.post(f'/orders/{oid}/status',{'Status':'Delivered'}).status_code==200
    assert client.get(f'/orders/{oid}').json['trip']['Status']=='Completed'
    assert admin.request('PUT',f'/orders/{oid}/trip',trip_data()).status_code==409
    heavy=new_order(client,items=[{**order_data()['items'][0],'WeightKg':'25000'}],PickupDate='2026-12-01')
    admin.post(f'/orders/{heavy}/status',{'Status':'Confirmed'})
    assert admin.request('PUT',f'/orders/{heavy}/trip',trip_data('2026-12-01')).status_code==409


def test_concurrent_trip_assignments(app,actors):
    admin,client,_=actors;ids=[new_order(client,PickupDate='2026-12-10') for _ in range(2)]
    for oid in ids:assert admin.post(f'/orders/{oid}/status',{'Status':'Confirmed'}).status_code==200
    def schedule(oid):
        actor=Actor(app);actor.post('/auth/login',admin.credentials)
        return actor.request('PUT',f'/orders/{oid}/trip',trip_data('2026-12-10',VehicleID=4,DriverID=2)).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:statuses=list(pool.map(schedule,ids))
    assert sorted(statuses)==[200,409],statuses


def test_catalog_snapshot_policy(actors):
    admin,client,_=actors;oid=new_order(client)
    before=client.get(f'/orders/{oid}').json['order']['QuotedAmount']
    response=admin.request('PUT','/catalogs/Routes/1',{'FromCityID':1,'ToCityID':2,'DistanceKm':'1501.00'})
    assert response.status_code==200,response.json
    assert client.get(f'/orders/{oid}').json['order']['QuotedAmount']==before
    assert admin.request('PUT','/catalogs/Routes/1',{'FromCityID':1,'ToCityID':2,'DistanceKm':'1500.00'}).status_code==200
    tariff=admin.get('/catalogs').json['data']['Tariffs'][0]
    payload={k:tariff[k] for k in ['Name','VehicleTypeID','BasePrice','PricePerKm','PricePerKg','IsActive']};payload['BasePrice']='999.00'
    assert admin.request('PUT','/catalogs/Tariffs/1',payload).status_code==409


def upload(actor,name,raw,oid=None):
    data={'Title':'Тест құжат','Category':'other','file':(io.BytesIO(raw),name)}
    if oid:data['OrderID']=str(oid)
    return actor.client.post('/api/documents',data=data,headers={'X-CSRF-Token':actor.token},content_type='multipart/form-data')


def basic_docx():
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w') as z:
        z.writestr('[Content_Types].xml','<Types/>')
        z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>&lt;script&gt;Қазақша&lt;/script&gt;</w:t></w:r></w:p></w:body></w:document>')
    return buf.getvalue()


def test_documents_bytes_preview_ownership_and_persistence(app,actors):
    admin,client,other=actors;oid=new_order(client)
    image=io.BytesIO();Image.new('RGB',(4,4),'blue').save(image,format='PNG')
    pdf=io.BytesIO();writer=PdfWriter();writer.add_blank_page(width=100,height=100);writer.write(pdf)
    files=[('test.txt','Сәлем <script>'.encode()),('test.png',image.getvalue()),('test.pdf',pdf.getvalue()),('test.docx',basic_docx())]
    for name,raw in files:
        response=upload(client,name,raw,oid);assert response.status_code==201,response.json;did=response.json['id']
        assert client.get(f'/documents/{did}/file').data==raw
        assert client.get(f'/documents/{did}/preview').status_code==200
        assert other.get(f'/documents/{did}/file').status_code==404
        assert other.request('DELETE',f'/documents/{did}').status_code==404
        with transaction() as q:assert bytes(q.scalar('SELECT Content FROM dbo.Documents WHERE DocumentID=?',(did,)))==raw
    did=upload(admin,'admin.txt',b'Admin document',oid).json['id']
    assert client.get(f'/documents/{did}/file').status_code==200
    assert client.request('DELETE',f'/documents/{did}').status_code==403
    # Fresh Flask application and connection read the same persisted SQL bytes.
    from backend.app import create_app
    reopened=Actor(create_app({'TESTING':True}));reopened.post('/auth/login',client.credentials)
    assert reopened.get(f'/documents/{did}/file').data==b'Admin document'
    assert all('Content' not in d for d in client.get('/documents').json['rows'])
    assert upload(other,'bad.txt',b'no',oid).status_code==404


@pytest.mark.parametrize('name,raw',[('fake.png',b'not png'),('a.txt',b'\x00'),('a.exe',b'MZ'),('a.pdf',b'%PDF-1.7 /JavaScript'),('a.docx',b'PK broken')])
def test_reject_bad_files(actors,name,raw):
    assert upload(actors[1],name,raw).status_code in (400,415)


def test_docx_external_entity_and_macro(actors):
    for path,content in [('word/vbaProject.bin',b'macro'),('word/evil.xml',b'<!DOCTYPE foo [<!ENTITY x SYSTEM "file:///secret">]><foo>&x;</foo>')]:
        buf=io.BytesIO(basic_docx())
        with zipfile.ZipFile(buf,'a') as z:z.writestr(path,content)
        assert upload(actors[1],'bad.docx',buf.getvalue()).status_code==400
    good=upload(actors[1],'safe.docx',basic_docx()).json['id']
    html=actors[1].get(f'/documents/{good}/preview').json['html']
    assert '<script>' not in html and '&lt;script&gt;' in html


def test_support_ownership_closed_and_reopen(actors):
    admin,client,other=actors;oid=new_order(client)
    tid=client.post('/support',{'Subject':'Көмек','Body':'Сұрақ','OrderID':oid}).json['id']
    assert other.get(f'/support/{tid}').status_code==404
    assert other.post(f'/support/{tid}/messages',{'Body':'bad'}).status_code==404
    assert admin.post(f'/support/{tid}/messages',{'Body':'Жауап'}).status_code==201
    assert len(client.get(f'/support/{tid}').json['messages'])==2
    assert admin.request('PATCH',f'/support/{tid}',{'Status':'Closed'}).status_code==200
    assert client.post(f'/support/{tid}/messages',{'Body':'Жаңа'}).status_code==409
    admin.request('PATCH',f'/support/{tid}',{'Status':'Open'})
    assert client.post(f'/support/{tid}/messages',{'Body':'Рақмет'}).status_code==201


def test_password_blocking_and_failed_attempts(app,actors):
    admin,client,_=actors;second=Actor(app);second.post('/auth/login',client.credentials)
    assert client.post('/auth/password',{'CurrentPassword':client.credentials['Password'],'Password':'Changed-'+secrets.token_hex(10)}).status_code==200
    assert second.get('/orders').status_code==401
    assert client.get('/orders').status_code==200
    assert admin.request('PATCH','/auth/users/'+str(client.user['UserID']),{'IsActive':False}).status_code==200
    assert client.get('/orders').status_code==401
    admin.request('PATCH','/auth/users/'+str(client.user['UserID']),{'IsActive':True})
    for _ in range(5):assert second.post('/auth/login',{**client.credentials,'Password':'bad-password'}).status_code==401
    with transaction() as q:
        row=q.one('SELECT FailedAttempts,LockedUntil FROM dbo.Users WHERE UserID=?',(client.user['UserID'],))
        assert row['FailedAttempts']==5 and row['LockedUntil'] is not None


def test_reports_local_day_csv_and_scope(actors):
    admin,client,other=actors;oid=new_order(client)
    with transaction(True) as q:q.execute("UPDATE dbo.Orders SET OrderDate='2026-11-19T19:30:00' WHERE OrderID=?",(oid,))
    r=client.get('/reports/orders?from=2026-11-20&to=2026-11-20').json
    assert r['count']==1 and r['totals']['QuotedAmount']=='196503.75'
    assert client.get('/reports/orders?from=2026-11-19&to=2026-11-19').json['count']==0
    assert other.get('/reports/orders').json['count']==0
    assert client.get('/reports/fleet').status_code==403
    with transaction(True) as q:q.execute('UPDATE dbo.Clients SET Name=? WHERE ClientID=?',('=DANGEROUS()',client.user['ClientID']))
    csv=client.get('/reports/orders?format=csv').data.decode('utf-8-sig')
    assert "'=DANGEROUS()" in csv


def test_sql_multirow_and_history_guards(actors):
    _,client,_=actors;ids=[new_order(client) for _ in range(2)]
    with transaction(True) as q:
        q.execute('INSERT dbo.CargoItems(OrderID,CargoTypeID,Description,WeightKg,VolumeM3,Quantity) VALUES (?,1,N\'Жүк\',1,1,1),(?,1,N\'Жүк\',2,1,1)',ids)
    with transaction() as q:
        assert q.scalar('SELECT QuotedAmount FROM dbo.Orders WHERE OrderID=?',(ids[0],))==Decimal('196518.75')
        assert q.scalar('SELECT QuotedAmount FROM dbo.Orders WHERE OrderID=?',(ids[1],))==Decimal('196533.75')
    with pytest.raises(Exception):
        with transaction(True) as q:q.execute('DELETE dbo.OrderStatusHistory WHERE OrderID=?',(ids[0],))


def test_real_backup_verify_disposable_database(test_database):
    conn=connect('master',True);path=None
    try:
        cur=conn.cursor();folder=cur.execute("SELECT CONVERT(nvarchar(4000),SERVERPROPERTY('InstanceDefaultBackupPath'))").fetchone()[0]
        path=folder.rstrip('\\/')+'\\'+test_database+'.bak'
        cur.execute(f'BACKUP DATABASE [{test_database}] TO DISK=? WITH COPY_ONLY,CHECKSUM',(path,));consume(cur)
        cur.execute('RESTORE VERIFYONLY FROM DISK=? WITH CHECKSUM',(path,));consume(cur);cur.close()
    finally:
        conn.close()
        if path:
            file=Path(path)
            assert file.name==test_database+'.bak'
            # SQL Server owns its backup directory. Successful BACKUP/VERIFYONLY
            # must not depend on the test user's right to remove server files.
            try:file.unlink(missing_ok=True)
            except PermissionError:
                import warnings
                warnings.warn('SQL service backup retained for administrator cleanup: '+str(file))
