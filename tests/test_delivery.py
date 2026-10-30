import pytest
from backend.db import transaction,connect
from backend.migrate import apply_migrations
from conftest import Actor,new_order,order_data

def test_contacts_tracking_privacy_and_notifications(app,actors):
    admin,client,other=actors
    oid=new_order(client)
    detail=client.get(f'/orders/{oid}').json['order']
    assert detail['SenderName']=='Тест жіберуші' and detail['PickupWindowStart']=='09:00'
    assert len(detail['TrackingCode'])==64
    public=Actor(app)
    tracked=public.post('/public/tracking',{'code':detail['TrackingCode'].lower()})
    assert tracked.status_code==200
    assert set(tracked.json['order'])=={'OrderNumber','Status','PickupDate','FromCity','ToCity','ExpectedArrivalAt','UpdatedAt'}
    assert set(tracked.json['history'][0])=={'NewStatus','ChangedAt'}
    assert public.post('/public/tracking',{'code':detail['OrderNumber']}).status_code==404
    assert public.post('/public/tracking',{'code':'A'*64}).status_code==404
    assert other.get(f'/orders/{oid}').status_code==404
    notices=admin.get('/notifications').json
    row=next(r for r in notices['rows'] if r['OrderID']==oid)
    assert row['EventType']=='order_created' and row['ReadAt'] is None
    nid=row['NotificationID']
    assert other.post(f'/notifications/{nid}/read').status_code==404
    assert public.get('/notifications').status_code==401
    assert admin.post(f'/notifications/{nid}/read').status_code==200
    read_at=next(r for r in admin.get('/notifications').json['rows'] if r['NotificationID']==nid)['ReadAt']
    admin.post(f'/notifications/{nid}/read')
    assert next(r for r in admin.get('/notifications').json['rows'] if r['NotificationID']==nid)['ReadAt']==read_at
    assert admin.post(f'/orders/{oid}/status',{'Status':'Confirmed'}).status_code==200
    assert client.get('/notifications').json['unread']==1
    assert other.get('/notifications').json['unread']==0
    assert public.post('/public/tracking',{'code':detail['TrackingCode']}).json['order']['Status']=='Confirmed'
    assert client.post('/notifications/read-all').status_code==200
    assert client.get('/notifications').json['unread']==0
    # A new app/client session still reads the durable SQL inbox and tracking code.
    again=Actor(app);assert again.post('/auth/login',client.credentials).status_code==200
    assert again.get('/notifications').json['rows'][0]['ReadAt'] is not None
    assert again.get(f'/orders/{oid}').json['order']['TrackingCode']==detail['TrackingCode']

@pytest.mark.parametrize('change',[{'SenderName':''},{'RecipientPhone':'not-a-phone'},
    {'PickupAddress':''},{'PickupWindowStart':'24:00'},{'PickupWindowEnd':'08:00'},{'PickupWindowEnd':None}])
def test_invalid_delivery_is_atomic(actors,change):
    _,client,_=actors
    with transaction() as q:
        before=(q.scalar('SELECT COUNT(*) FROM dbo.Orders'),q.scalar('SELECT COUNT(*) FROM dbo.Notifications'))
    assert client.post('/orders',order_data(**change)).status_code==400
    with transaction() as q:
        after=(q.scalar('SELECT COUNT(*) FROM dbo.Orders'),q.scalar('SELECT COUNT(*) FROM dbo.Notifications'))
    assert before==after

def test_delivery_edit_and_failed_edit_roll_back(actors):
    admin,client,_=actors;oid=new_order(client)
    body=order_data(DeliveryAddress='Жаңа мекенжай, 42');body.pop('items')
    assert client.request('PUT',f'/orders/{oid}',body).status_code==403
    assert admin.request('PUT',f'/orders/{oid}',body).status_code==200
    assert client.get(f'/orders/{oid}').json['order']['DeliveryAddress']=='Жаңа мекенжай, 42'
    assert client.get('/notifications').json['rows'][0]['EventType']=='delivery_updated'
    assert admin.request('PUT',f'/orders/{oid}',{**body,'PickupDate':'2026-12-01','SenderPhone':'bad'}).status_code==400
    assert client.get(f'/orders/{oid}').json['order']['PickupDate']=='2026-11-20'

def test_migration_repeat_preserves_data(actors):
    _,client,_=actors;oid=new_order(client)
    before=client.get(f'/orders/{oid}').json
    c=connect()
    try:apply_migrations(c);c.commit()
    finally:c.close()
    assert client.get(f'/orders/{oid}').json==before
