"""Delivery contacts, public tracking projection and per-user inbox."""
import re
from datetime import time
from flask import Blueprint,request,jsonify,g
from .schema import string,integer
from .errors import require
from .db import transaction
from .auth import protected

bp=Blueprint('delivery',__name__,url_prefix='/api')
CONTACT_FIELDS={'SenderName':120,'SenderPhone':30,'PickupAddress':250,
                'RecipientName':120,'RecipientPhone':30,'DeliveryAddress':250}
DELIVERY_FIELDS=set(CONTACT_FIELDS)|{'PickupWindowStart','PickupWindowEnd'}

def delivery_values(data):
    values={key:string(data.get(key),size,key) for key,size in CONTACT_FIELDS.items()}
    for key in ('SenderPhone','RecipientPhone'):
        require(re.fullmatch(r'\+?[0-9 ()-]{7,30}',values[key]) and 7<=len(re.sub(r'\D','',values[key]))<=15,'phone_invalid',field=key)
    for key in ('PickupWindowStart','PickupWindowEnd'):
        raw=data.get(key)
        require(isinstance(raw,str) and re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d(?::00)?',raw),'time_invalid',field=key)
        values[key]=time.fromisoformat(raw)
    require(values['PickupWindowEnd']>values['PickupWindowStart'],'pickup_window',field='PickupWindowEnd')
    return values

def notify_order(q,oid,event,status=None,audience='client'):
    if audience=='admin':
        recipients=q.rows("SELECT UserID FROM dbo.Users WHERE Role='admin' AND IsActive=1")
    else:
        recipients=q.rows('SELECT u.UserID FROM dbo.Users u JOIN dbo.Orders o ON o.ClientID=u.ClientID WHERE o.OrderID=? AND u.IsActive=1',(oid,))
    for recipient in recipients:
        q.insert('Notifications','NotificationID',dict(UserID=recipient['UserID'],OrderID=oid,EventType=event,NewStatus=status))

@bp.post('/public/tracking')
def tracking():
    data=request.get_json();require(isinstance(data,dict),'invalid')
    code=str(data.get('code','')).strip().upper()
    require(re.fullmatch(r'[0-9A-F]{64}',code),'tracking_not_found',404)
    with transaction() as q:
        row=q.one('''SELECT o.OrderID,o.OrderNumber,o.Status,o.PickupDate,f.Name AS FromCity,t.Name AS ToCity,
            CASE WHEN tr.Status IN('Planned','InTransit','Completed') THEN tr.ArrivalAt END AS ExpectedArrivalAt,
            (SELECT MAX(h.ChangedAt) FROM dbo.OrderStatusHistory h WHERE h.OrderID=o.OrderID) AS UpdatedAt
            FROM dbo.Orders o JOIN dbo.Routes r ON r.RouteID=o.RouteID
            JOIN dbo.Cities f ON f.CityID=r.FromCityID JOIN dbo.Cities t ON t.CityID=r.ToCityID
            LEFT JOIN dbo.Trips tr ON tr.OrderID=o.OrderID WHERE o.TrackingCode=?''',(code,))
        require(row,'tracking_not_found',404)
        oid=row.pop('OrderID')
        history=q.rows('SELECT NewStatus,ChangedAt FROM dbo.OrderStatusHistory WHERE OrderID=? ORDER BY HistoryID',(oid,))
        return jsonify(order=row,history=history)

@bp.get('/notifications')
@protected()
def notifications():
    before=integer(request.args['before']) if request.args.get('before') else 2147483647
    rows=g.q.rows('''SELECT TOP(30) n.*,o.OrderNumber FROM dbo.Notifications n
        JOIN dbo.Orders o ON o.OrderID=n.OrderID WHERE n.UserID=? AND n.NotificationID<?
        ORDER BY n.NotificationID DESC''',(g.user['UserID'],before))
    unread=g.q.scalar('SELECT COUNT(*) FROM dbo.Notifications WHERE UserID=? AND ReadAt IS NULL',(g.user['UserID'],))
    return jsonify(rows=rows,unread=unread,nextBefore=rows[-1]['NotificationID'] if len(rows)==30 else None)

@bp.post('/notifications/read-all')
@protected(write=True)
def read_all():
    g.q.execute('UPDATE dbo.Notifications SET ReadAt=SYSUTCDATETIME() WHERE UserID=? AND ReadAt IS NULL',(g.user['UserID'],))
    return jsonify(ok=True)

@bp.post('/notifications/<int:nid>/read')
@protected(write=True)
def read_one(nid):
    require(g.q.scalar('SELECT NotificationID FROM dbo.Notifications WHERE NotificationID=? AND UserID=?',(nid,g.user['UserID'])),'not_found',404)
    g.q.execute('UPDATE dbo.Notifications SET ReadAt=COALESCE(ReadAt,SYSUTCDATETIME()) WHERE NotificationID=? AND UserID=?',(nid,g.user['UserID']))
    return jsonify(ok=True)
