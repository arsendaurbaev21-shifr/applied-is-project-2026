"""Role-scoped search and versioned SQL drafts with atomic, idempotent submission."""
import json
from uuid import UUID
from flask import Blueprint,g,request,jsonify
from .auth import protected
from .errors import require
from .service import create_order
from .delivery import CONTACT_FIELDS

bp=Blueprint('usability',__name__,url_prefix='/api')
STATES=('New','Confirmed','InTransit','Delivered','Cancelled')

def like_pattern(value):
    return '%'+str(value).replace('[','[[]').replace('%','[%]').replace('_','[_]')+'%'

@bp.get('/search')
@protected()
def search():
    term=request.args.get('q','').strip()
    require(len(term)<=120,'invalid',field='search')
    if len(term)<2:return jsonify(orders=[],clients=[],routes=[],cities=[])
    pattern=like_pattern(term)
    scope=' AND ClientID=?' if g.user['Role']=='client' else ''
    params=[pattern]*4+([g.user['ClientID']] if scope else [])
    orders=g.q.rows('''SELECT TOP(12) OrderID,OrderNumber,ClientName,FromCity,ToCity,Status
        FROM dbo.v_OrderOverview WHERE (OrderNumber LIKE ? OR ClientName LIKE ? OR FromCity LIKE ? OR ToCity LIKE ?)'''+scope+' ORDER BY OrderID DESC',params)
    clients=[];routes=[];cities=[]
    if g.user['Role']=='admin':
        clients=g.q.rows('SELECT TOP(6) ClientID,Name FROM dbo.Clients WHERE Name LIKE ? OR Email LIKE ? OR Phone LIKE ? ORDER BY Name,ClientID',(pattern,)*3)
        cities=g.q.rows('SELECT TOP(6) CityID,Name FROM dbo.Cities WHERE Name LIKE ? ORDER BY Name,CityID',(pattern,))
        routes=g.q.rows('''SELECT TOP(6) r.RouteID,f.Name AS FromCity,t.Name AS ToCity,r.DistanceKm
            FROM dbo.Routes r JOIN dbo.Cities f ON f.CityID=r.FromCityID JOIN dbo.Cities t ON t.CityID=r.ToCityID
            WHERE f.Name LIKE ? OR t.Name LIKE ? ORDER BY r.RouteID''',(pattern,pattern))
    return jsonify(orders=orders,clients=clients,routes=routes,cities=cities)

def client_only():require(g.user['Role']=='client','client_only',403)

def draft_key(value):
    try:result=str(UUID(str(value)))
    except (ValueError,TypeError,AttributeError):require(False,'invalid',field='DraftKey')
    require(result==value,'invalid',field='DraftKey')
    return result

def clean_payload(value):
    limits={**CONTACT_FIELDS,'RouteID':20,'TariffID':20,'PickupDate':10,'Notes':500,'PickupWindowStart':8,'PickupWindowEnd':8}
    require(isinstance(value,dict) and not set(value)-set(limits)-{'items'},'unknown_field')
    result={}
    for key,size in limits.items():
        if key in value:
            require(isinstance(value[key],(str,int,float)) and not isinstance(value[key],bool),'invalid',field=key)
            result[key]=str(value[key]);require(len(result[key])<=size,'too_long',field=key)
    items=value.get('items',[]);require(isinstance(items,list) and len(items)<=100,'cargo_required')
    result['items']=[]
    for item in items:
        sizes={'CargoTypeID':20,'Description':200,'WeightKg':30,'VolumeM3':30,'Quantity':20}
        require(isinstance(item,dict) and not set(item)-set(sizes),'unknown_field')
        cleaned={}
        for key,val in item.items():
            require(isinstance(val,(str,int,float)) and not isinstance(val,bool),'invalid',field=key)
            cleaned[key]=str(val);require(len(cleaned[key])<=sizes[key],'too_long',field=key)
        result['items'].append(cleaned)
    payload=json.dumps(result,ensure_ascii=False,separators=(',',':'))
    require(len(payload.encode('utf-8'))<=60000,'too_long')
    return payload

def draft_json(row):
    if not row:return None
    return dict(key=row['DraftKey'],revision=row['Revision'],step=row['Step'],updatedAt=row['UpdatedAt'],payload=json.loads(row['Payload']))

@bp.get('/drafts/current')
@protected()
def current_draft():
    client_only()
    row=g.q.one('SELECT * FROM dbo.OrderDrafts WHERE UserID=? AND SubmittedOrderID IS NULL',(g.user['UserID'],))
    return jsonify(draft=draft_json(row))

@bp.put('/drafts/<key>')
@protected(write=True)
def save_draft(key):
    client_only();draft_key(key);body=request.get_json();require(isinstance(body,dict),'invalid')
    revision=body.get('revision');step=body.get('step',0)
    require(type(revision) is int and revision>=0 and type(step) is int and 0<=step<=3,'invalid')
    payload=clean_payload(body.get('payload'))
    row=g.q.one('SELECT * FROM dbo.OrderDrafts WHERE DraftKey=?',(key,))
    if row:
        require(row['UserID']==g.user['UserID'],'not_found',404)
        require(row['SubmittedOrderID'] is None,'draft_closed',409)
        require(row['Revision']==revision,'draft_conflict',409)
        g.q.execute('UPDATE dbo.OrderDrafts SET Payload=?,Step=?,Revision=Revision+1,UpdatedAt=SYSUTCDATETIME() WHERE DraftKey=?',(payload,step,key))
    else:
        require(revision==0,'draft_conflict',409)
        require(not g.q.scalar('SELECT DraftID FROM dbo.OrderDrafts WHERE UserID=? AND SubmittedOrderID IS NULL',(g.user['UserID'],)),'draft_conflict',409)
        g.q.insert('OrderDrafts','DraftID',dict(DraftKey=key,UserID=g.user['UserID'],Payload=payload,Step=step))
    return jsonify(draft=draft_json(g.q.one('SELECT * FROM dbo.OrderDrafts WHERE DraftKey=?',(key,))))

@bp.delete('/drafts/<key>')
@protected(write=True)
def discard_draft(key):
    client_only();draft_key(key);body=request.get_json();require(isinstance(body,dict),'invalid');require(type(body.get('revision')) is int and body['revision']>=0,'invalid')
    row=g.q.one('SELECT * FROM dbo.OrderDrafts WHERE DraftKey=? AND UserID=?',(key,g.user['UserID']))
    require(row,'not_found',404);require(row['SubmittedOrderID'] is None,'draft_closed',409)
    require(row['Revision']==body.get('revision'),'draft_conflict',409)
    g.q.execute('DELETE dbo.OrderDrafts WHERE DraftID=?',(row['DraftID'],))
    return jsonify(ok=True)

@bp.post('/drafts/<key>/submit')
@protected(write=True)
def submit_draft(key):
    client_only();draft_key(key);body=request.get_json();require(isinstance(body,dict),'invalid');require(type(body.get('revision')) is int and body['revision']>=0,'invalid')
    row=g.q.one('SELECT * FROM dbo.OrderDrafts WHERE DraftKey=? AND UserID=?',(key,g.user['UserID']))
    require(row,'not_found',404)
    if row['SubmittedOrderID'] is not None:return jsonify(id=row['SubmittedOrderID'],replayed=True)
    require(row['Revision']==body.get('revision'),'draft_conflict',409)
    oid=create_order(g.q,g.user,json.loads(row['Payload']))
    g.q.execute("UPDATE dbo.OrderDrafts SET SubmittedOrderID=?,Payload=N'{}',UpdatedAt=SYSUTCDATETIME(),Revision=Revision+1 WHERE DraftID=?",(oid,row['DraftID']))
    return jsonify(id=oid,replayed=False),201
