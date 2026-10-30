from uuid import uuid4
from urllib.parse import quote
import pytest
from conftest import Actor,order_data,new_order
from backend.db import transaction

def save(actor,key,payload,revision=0,step=0):
    return actor.request('PUT','/drafts/'+key,dict(payload=payload,revision=revision,step=step))

def test_draft_partial_resume_ownership_and_conflict(app,actors):
    admin,client,other=actors;key=str(uuid4())
    assert client.get('/drafts/current').json['draft'] is None
    partial={'SenderName':'Жіберуші','RecipientPhone':'unfinished','items':[{'Description':'Қорап'}]}
    first=save(client,key,partial,step=1);assert first.status_code==200,first.json
    draft=first.json['draft'];assert draft['revision']==1 and draft['step']==1
    assert draft['payload']['RecipientPhone']=='unfinished'
    assert other.get('/drafts/current').json['draft'] is None
    assert save(other,key,partial,revision=1).status_code==404
    assert other.post('/drafts/'+key+'/submit',{'revision':1}).status_code==404
    assert other.request('DELETE','/drafts/'+key,{'revision':1}).status_code==404
    assert admin.get('/drafts/current').status_code==403
    assert save(admin,str(uuid4()),{}).status_code==403
    second=save(client,key,{**partial,'Notes':'new'},revision=1);assert second.json['draft']['revision']==2
    assert save(client,key,{**partial,'Notes':'stale'},revision=1).status_code==409
    assert save(client,str(uuid4()),{}).status_code==409
    assert client.request('DELETE','/drafts/'+key,{'revision':1}).status_code==409
    again=Actor(app);assert again.post('/auth/login',client.credentials).status_code==200
    assert again.get('/drafts/current').json['draft']['payload']['Notes']=='new'
    assert client.request('DELETE','/drafts/'+key,{'revision':2}).status_code==200
    assert client.get('/drafts/current').json['draft'] is None

def test_submit_atomic_idempotent_and_no_draft_notifications(actors):
    admin,client,_=actors;key=str(uuid4())
    with transaction() as q:before=(q.scalar('SELECT COUNT(*) FROM dbo.Orders'),q.scalar('SELECT COUNT(*) FROM dbo.Notifications'))
    assert save(client,key,{'SenderName':'partial','items':[]}).status_code==200
    response=client.post('/drafts/'+key+'/submit',{'revision':1});assert response.status_code==400
    with transaction() as q:assert before==(q.scalar('SELECT COUNT(*) FROM dbo.Orders'),q.scalar('SELECT COUNT(*) FROM dbo.Notifications'))
    assert client.get('/drafts/current').json['draft']['revision']==1
    updated=save(client,key,order_data(),revision=1,step=3);assert updated.status_code==200
    assert client.post('/drafts/'+key+'/submit',{'revision':1}).status_code==409
    response=client.post('/drafts/'+key+'/submit',{'revision':2});assert response.status_code==201,response.json
    oid=response.json['id']
    retry=client.post('/drafts/'+key+'/submit',{'revision':2});assert retry.status_code==200 and retry.json['id']==oid and retry.json['replayed']
    assert client.get('/drafts/current').json['draft'] is None
    assert save(client,key,order_data(),revision=2).status_code==409
    assert client.request('DELETE','/drafts/'+key,{'revision':3}).status_code==409
    with transaction() as q:
        assert q.scalar('SELECT COUNT(*) FROM dbo.Orders')==before[0]+1
        assert q.scalar('SELECT Payload FROM dbo.OrderDrafts WHERE DraftKey=?',(key,))=='{}'
        assert q.scalar('SELECT COUNT(*) FROM dbo.Notifications WHERE OrderID=? AND UserID=?',(oid,admin.user['UserID']))==1
    assert save(client,str(uuid4()),{}).status_code==200

@pytest.mark.parametrize('payload',[{'UserID':1},{'items':[{'OrderID':2}]},{'items':[None]},
    {'SenderName':'a'*121},{'items':[{}]*101},{'items':'bad'},{'Notes':{'x':1}}])
def test_draft_payload_is_bounded(actors,payload):
    _,client,_=actors
    assert save(client,str(uuid4()),payload).status_code==400
    assert client.get('/drafts/current').json['draft'] is None

def test_search_scope_cities_and_status_counts(app,actors):
    admin,client,other=actors;oid=new_order(client);other_id=new_order(other)
    order=client.get('/orders/'+str(oid)).json['order'];number=order['OrderNumber']
    result=client.get('/search?q='+number).json
    assert [r['OrderID'] for r in result['orders']]==[oid]
    assert not result['clients'] and not result['cities'] and not result['routes']
    assert other.get('/search?q='+number).json['orders']==[]
    by_city=client.get('/search?q='+quote('Астана')).json
    assert {r['OrderID'] for r in by_city['orders']}=={oid}
    assert client.get('/orders?search='+quote('Астана')).json['totals']['Count']==1
    admin_result=admin.get('/search?q='+quote('Астана')).json
    assert admin_result['cities'] and admin_result['routes']
    assert {oid,other_id}<=set(r['OrderID'] for r in admin_result['orders'])
    assert client.get('/search?q='+quote('%_')).json['orders']==[]
    assert client.get('/search?q='+('x'*121)).status_code==400
    assert not client.get('/search?q=A').json['orders']
    assert Actor(app).get('/search?q=test').status_code==401
    second=new_order(client)
    assert admin.post(f'/orders/{second}/status',{'Status':'Confirmed'}).status_code==200
    response=client.get('/orders?status=Confirmed').json
    assert len(response['rows'])==1
    assert response['statusCounts']['New']==1 and response['statusCounts']['Confirmed']==1
    assert set(response['rows'][0]).isdisjoint({'TrackingCode','SenderPhone','RecipientPhone'})


def test_draft_invalid_command_body(actors):
    _,client,_=actors;key=str(uuid4())
    assert save(client,key,{}).status_code==200
    for body in (['bad'],[],{'revision':True},{'revision':'1'},{'revision':-1}):
        assert client.post('/drafts/'+key+'/submit',body).status_code==400
        assert client.request('DELETE','/drafts/'+key,body).status_code==400
    assert client.get('/drafts/current').json['draft']['revision']==1
