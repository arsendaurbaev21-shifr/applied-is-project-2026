"""Public catalog, role-scoped operations, support, and exact-decimal reports."""
import csv
import io
from datetime import datetime,timedelta,time,timezone
from decimal import Decimal
from flask import Blueprint,request,jsonify,g,Response
from .auth import protected
from .db import transaction
from .schema import CATALOGS,catalog_payload,integer,string,calendar_date,local_zone,local_to_utc,dec
from .errors import require
from .service import own_order,quote,create_order,change_status,cargo_values,editable,save_trip
from .delivery import DELIVERY_FIELDS,delivery_values,notify_order
from .usability import like_pattern,STATES

bp=Blueprint('portal',__name__,url_prefix='/api')


def catalogs(q,private=False):
    names=CATALOGS if private else ['Cities','Routes','VehicleTypes','CargoTypes','Tariffs']
    return {name:q.rows(f'SELECT * FROM dbo.[{name}]'+(' WHERE IsActive=1' if name=='Tariffs' and not private else '')+f' ORDER BY [{CATALOGS[name][0]}]') for name in names}


@bp.get('/public/catalogs')
def public_catalogs():
    with transaction() as q: return jsonify(data=catalogs(q),timezone=str(local_zone()))


@bp.get('/public/quote')
def public_quote():
    with transaction() as q:
        return jsonify(amount=quote(q,request.args.get('RouteID'),request.args.get('TariffID'),request.args.get('WeightKg')))


@bp.get('/catalogs')
@protected(admin=True)
def admin_catalogs(): return jsonify(data=catalogs(g.q,True),schema={k:{'pk':v[0],'fields':v[1]} for k,v in CATALOGS.items()},timezone=str(local_zone()))


@bp.route('/catalogs/<table>',methods=['POST'])
@bp.route('/catalogs/<table>/<int:record_id>',methods=['PUT','DELETE'])
@protected(admin=True,write=True)
def catalog_change(table,record_id=None):
    require(table in CATALOGS,'not_found',404)
    pk=CATALOGS[table][0]
    if record_id:
        require(g.q.scalar(f'SELECT [{pk}] FROM dbo.[{table}] WHERE [{pk}]=?',(record_id,)),'not_found',404)
    if request.method=='DELETE': g.q.execute(f'DELETE dbo.[{table}] WHERE [{pk}]=?',(record_id,))
    else:
        values=catalog_payload(table,request.get_json())
        if table=='Routes':values.update(DistanceSource=None,DistanceUpdatedAt=None)
        if record_id:
            g.q.execute(f'UPDATE dbo.[{table}] SET '+','.join('['+f+']=?' for f in values)+f' WHERE [{pk}]=?',(*values.values(),record_id))
            if table=='Clients':
                g.q.execute('UPDATE dbo.Users SET FullName=? WHERE ClientID=?',(values['Name'],record_id))
        else: record_id=g.q.insert(table,pk,values)
    return jsonify(ok=True,id=record_id)


@bp.get('/profile')
@protected()
def profile():
    return jsonify(user=g.user,client=g.q.one('SELECT * FROM dbo.Clients WHERE ClientID=?',(g.user['ClientID'],)) if g.user['ClientID'] else None)


@bp.put('/profile')
@protected(write=True)
def profile_save():
    data=request.get_json(); require(isinstance(data,dict),'invalid')
    name=string(data.get('FullName'),120,'FullName')
    g.q.execute('UPDATE dbo.Users SET FullName=? WHERE UserID=?',(name,g.user['UserID']))
    if g.user['Role']=='client':
        phone=string(data.get('Phone'),30,'Phone'); address=string(data.get('Address'),250,'Address',True)
        g.q.execute('UPDATE dbo.Clients SET Name=?,Phone=?,Address=? WHERE ClientID=?',(name,phone,address,g.user['ClientID']))
    return jsonify(ok=True)


def order_filter(user,params,alias='v'):
    where=[]; values=[]
    if user['Role']=='client': where.append(f'{alias}.ClientID=?'); values.append(user['ClientID'])
    if params.get('status'): where.append(f'{alias}.Status=?'); values.append(params['status'])
    if params.get('search'):
        where.append(f'({alias}.OrderNumber LIKE ? OR {alias}.ClientName LIKE ? OR {alias}.FromCity LIKE ? OR {alias}.ToCity LIKE ?)')
        values.extend([like_pattern(str(params['search'])[:120])]*4)
    return where,values


def date_filter(where,values,column,params):
    start=params.get('from'); end=params.get('to')
    if start and end: require(calendar_date(start)<=calendar_date(end),'date_range')
    if start:
        where.append(column+'>=?'); values.append(local_to_utc(datetime.combine(calendar_date(start),time.min)))
    if end:
        where.append(column+'<?'); values.append(local_to_utc(datetime.combine(calendar_date(end)+timedelta(days=1),time.min)))


def where_sql(where): return ' WHERE '+' AND '.join(where) if where else ''


@bp.get('/orders')
@protected()
def orders():
    where,values=order_filter(g.user,request.args)
    date_filter(where,values,'v.OrderDate',request.args)
    rows=g.q.rows('SELECT v.* FROM dbo.v_OrderOverview v'+where_sql(where)+' ORDER BY v.OrderID DESC',values)
    active=[r for r in rows if r['Status']!='Cancelled']
    totals={k:sum((r[k] for r in active),Decimal('0')) for k in ('QuotedAmount','PaidAmount','BalanceAmount')}
    totals.update(Count=len(rows),statuses={s:sum(r['Status']==s for r in rows) for s in ('New','Confirmed','InTransit','Delivered','Cancelled')})
    count_args=dict(request.args);count_args.pop('status',None)
    cw,cv=order_filter(g.user,count_args);date_filter(cw,cv,'v.OrderDate',count_args)
    counts={state:0 for state in STATES}
    for r in g.q.rows('SELECT v.Status,COUNT(*) AS N FROM dbo.v_OrderOverview v'+where_sql(cw)+' GROUP BY v.Status',cv):counts[r['Status']]=r['N']
    return jsonify(rows=rows,totals=totals,statusCounts=counts)


@bp.post('/orders')
@protected(write=True)
def order_create(): return jsonify(id=create_order(g.q,g.user,request.get_json())),201


@bp.get('/orders/<int:oid>')
@protected()
def order_detail(oid):
    raw=own_order(g.q,g.user,oid)
    overview=g.q.one('SELECT * FROM dbo.v_OrderOverview WHERE OrderID=?',(oid,))
    overview.update({key:raw[key] for key in DELIVERY_FIELDS|{'TrackingCode'}})
    return jsonify(order=overview,
                   items=g.q.rows('SELECT c.*,t.Name AS CargoType FROM dbo.CargoItems c JOIN dbo.CargoTypes t ON t.CargoTypeID=c.CargoTypeID WHERE OrderID=?',(oid,)),
                   payments=g.q.rows('SELECT * FROM dbo.Payments WHERE OrderID=? ORDER BY PaidAt,PaymentID',(oid,)),
                   history=g.q.rows('SELECT * FROM dbo.OrderStatusHistory WHERE OrderID=? ORDER BY HistoryID',(oid,)),
                   trip=g.q.one('SELECT * FROM dbo.Trips WHERE OrderID=?',(oid,)))


@bp.put('/orders/<int:oid>')
@protected(admin=True,write=True)
def edit_order(oid):
    order=own_order(g.q,g.user,oid); editable(g.q,order)
    data=request.get_json(); require(isinstance(data,dict),'invalid')
    route=integer(data.get('RouteID'),'RouteID'); tariff=integer(data.get('TariffID'),'TariffID')
    require(g.q.scalar('SELECT TariffID FROM dbo.Tariffs WHERE TariffID=? AND IsActive=1',(tariff,)),'catalog_missing')
    g.q.execute('UPDATE dbo.Orders SET RouteID=?,TariffID=?,PickupDate=?,Notes=? WHERE OrderID=?',
                (route,tariff,calendar_date(data.get('PickupDate')),string(data.get('Notes'),500,'Notes',True),oid))
    values=delivery_values(data)
    g.q.execute('UPDATE dbo.Orders SET '+','.join('['+key+']=?' for key in values)+' WHERE OrderID=?',(*values.values(),oid))
    notify_order(g.q,oid,'delivery_updated')
    return jsonify(ok=True)


@bp.post('/orders/<int:oid>/status')
@protected(write=True)
def status(oid):
    data=request.get_json(); require(isinstance(data,dict),'invalid')
    change_status(g.q,g.user,oid,data.get('Status'))
    return jsonify(ok=True)


@bp.post('/orders/<int:oid>/cargo')
@bp.route('/orders/<int:oid>/cargo/<int:cid>',methods=['PUT','DELETE'])
@protected(admin=True,write=True)
def cargo(oid,cid=None):
    order=own_order(g.q,g.user,oid); editable(g.q,order)
    if cid: require(g.q.scalar('SELECT CargoItemID FROM dbo.CargoItems WHERE CargoItemID=? AND OrderID=?',(cid,oid)),'not_found',404)
    if request.method=='DELETE': g.q.execute('DELETE dbo.CargoItems WHERE CargoItemID=?',(cid,))
    else:
        values=cargo_values(request.get_json())
        if cid: g.q.execute('UPDATE dbo.CargoItems SET '+','.join('['+k+']=?' for k in values)+' WHERE CargoItemID=?',(*values.values(),cid))
        else: cid=g.q.insert('CargoItems','CargoItemID',dict(OrderID=oid,**values))
    return jsonify(ok=True,id=cid)


@bp.put('/orders/<int:oid>/trip')
@protected(admin=True,write=True)
def trip(oid):
    data=request.get_json(); require(isinstance(data,dict),'invalid')
    return jsonify(id=save_trip(g.q,g.user,oid,data))


@bp.post('/orders/<int:oid>/payments')
@bp.route('/orders/<int:oid>/payments/<int:pid>',methods=['PUT','DELETE'])
@protected(admin=True,write=True)
def payment(oid,pid=None):
    own_order(g.q,g.user,oid)
    if pid: require(g.q.scalar('SELECT PaymentID FROM dbo.Payments WHERE PaymentID=? AND OrderID=?',(pid,oid)),'not_found',404)
    if request.method=='DELETE': g.q.execute('DELETE dbo.Payments WHERE PaymentID=?',(pid,))
    else:
        data=request.get_json(); require(isinstance(data,dict),'invalid')
        method=data.get('Method'); require(method in ('Cash','Card','Transfer'),'invalid',field='Method')
        values=dict(Amount=dec(data.get('Amount'),field='Amount'),Method=method,Note=string(data.get('Note'),250,'Note',True))
        if pid: g.q.execute('UPDATE dbo.Payments SET Amount=?,Method=?,Note=? WHERE PaymentID=?',(*values.values(),pid))
        else: pid=g.q.insert('Payments','PaymentID',dict(OrderID=oid,**values))
    return jsonify(ok=True,id=pid)


def ticket_owned(tid):
    row=g.q.one('SELECT * FROM dbo.SupportTickets WHERE TicketID=?',(tid,))
    require(row and (g.user['Role']=='admin' or row['UserID']==g.user['UserID']),'not_found',404)
    return row


@bp.get('/support')
@protected()
def tickets():
    return jsonify(rows=g.q.rows('SELECT t.*,u.FullName FROM dbo.SupportTickets t JOIN dbo.Users u ON u.UserID=t.UserID'+
        ('' if g.user['Role']=='admin' else ' WHERE t.UserID=?')+' ORDER BY t.UpdatedAt DESC,t.TicketID DESC',() if g.user['Role']=='admin' else (g.user['UserID'],)))


@bp.post('/support')
@protected(write=True)
def ticket_create():
    data=request.get_json(); require(isinstance(data,dict),'invalid')
    oid=integer(data['OrderID']) if data.get('OrderID') else None
    if oid: own_order(g.q,g.user,oid)
    tid=g.q.insert('SupportTickets','TicketID',dict(UserID=g.user['UserID'],OrderID=oid,Subject=string(data.get('Subject'),160,'Subject')))
    g.q.insert('TicketMessages','MessageID',dict(TicketID=tid,UserID=g.user['UserID'],Body=string(data.get('Body'),2000,'Body')))
    return jsonify(id=tid),201


@bp.get('/support/<int:tid>')
@protected()
def ticket_detail(tid):
    row=ticket_owned(tid)
    return jsonify(ticket=row,messages=g.q.rows('SELECT m.*,u.FullName,u.Role FROM dbo.TicketMessages m JOIN dbo.Users u ON u.UserID=m.UserID WHERE TicketID=? ORDER BY MessageID',(tid,)))


@bp.post('/support/<int:tid>/messages')
@protected(write=True)
def ticket_message(tid):
    row=ticket_owned(tid); require(row['Status']!='Closed','ticket_closed',409)
    data=request.get_json(); require(isinstance(data,dict),'invalid')
    mid=g.q.insert('TicketMessages','MessageID',dict(TicketID=tid,UserID=g.user['UserID'],Body=string(data.get('Body'),2000,'Body')))
    g.q.execute('UPDATE dbo.SupportTickets SET UpdatedAt=SYSUTCDATETIME() WHERE TicketID=?',(tid,))
    return jsonify(id=mid),201


@bp.patch('/support/<int:tid>')
@protected(admin=True,write=True)
def ticket_status(tid):
    ticket_owned(tid); data=request.get_json(); require(isinstance(data,dict),'invalid')
    value=data.get('Status'); require(value in ('Open','InProgress','Closed'),'invalid')
    g.q.execute('UPDATE dbo.SupportTickets SET Status=?,UpdatedAt=SYSUTCDATETIME() WHERE TicketID=?',(value,tid))
    return jsonify(ok=True)


@bp.get('/reports/<kind>')
@protected()
def report(kind):
    require(kind in ('orders','payments','clients','fleet'),'not_found',404)
    require(g.user['Role']=='admin' or kind in ('orders','payments'),'forbidden',403)
    where=[]; values=[]
    if kind=='orders':
        where,values=order_filter(g.user,request.args)
        date_filter(where,values,'v.OrderDate',request.args)
        sql='SELECT v.OrderNumber,v.ClientName,v.FromCity,v.ToCity,v.OrderDate,v.PickupDate,v.Status,v.QuotedAmount,v.PaidAmount,v.BalanceAmount FROM dbo.v_OrderOverview v'
        rows=g.q.rows(sql+where_sql(where)+' ORDER BY v.OrderID',values)
        totals={k:sum((r[k] for r in rows),Decimal(0)) for k in ('QuotedAmount','PaidAmount','BalanceAmount')}
    elif kind=='payments':
        if g.user['Role']=='client': where.append('o.ClientID=?'); values.append(g.user['ClientID'])
        date_filter(where,values,'p.PaidAt',request.args)
        rows=g.q.rows('SELECT p.PaymentID,o.OrderNumber,c.Name AS ClientName,p.Amount,p.PaidAt,p.Method,p.Note FROM dbo.Payments p JOIN dbo.Orders o ON o.OrderID=p.OrderID JOIN dbo.Clients c ON c.ClientID=o.ClientID'+where_sql(where)+' ORDER BY p.PaidAt,p.PaymentID',values)
        totals={'Amount':sum((r['Amount'] for r in rows),Decimal(0))}
    elif kind=='clients':
        rows=g.q.rows('SELECT ClientID,Name,Phone,Email,Address,CreatedAt FROM dbo.Clients ORDER BY ClientID'); totals={}
    else:
        rows=g.q.rows('SELECT v.PlateNumber,v.Brand,t.Name AS VehicleType,v.CapacityKg,v.IsActive FROM dbo.Vehicles v JOIN dbo.VehicleTypes t ON t.VehicleTypeID=v.VehicleTypeID ORDER BY v.VehicleID'); totals={}
    filters=dict(request.args) if kind in ('orders','payments') else {}
    generated=datetime.now(timezone.utc).isoformat()
    if request.args.get('format')=='csv':
        buffer=io.StringIO(); writer=csv.writer(buffer)
        def safe(v):
            text='' if v is None else str(v)
            return "'"+text if text.lstrip().startswith(('=','+','-','@','\t','\r','\n')) else text
        writer.writerow(['QazCargo',kind,generated,str(local_zone())])
        writer.writerow(['Filters',str({k:v for k,v in filters.items() if k!='format'})])
        if rows:
            writer.writerow(rows[0].keys())
            writer.writerows([[safe(v) for v in row.values()] for row in rows])
        writer.writerow(['Rows',len(rows)])
        for k,v in totals.items(): writer.writerow([k,v])
        return Response('\ufeff'+buffer.getvalue(),mimetype='text/csv; charset=utf-8',headers={'Content-Disposition':f'attachment; filename="QazCargo_{kind}.csv"'})
    return jsonify(rows=rows,totals=totals,filters=filters,generated=generated,timezone=str(local_zone()),count=len(rows))
