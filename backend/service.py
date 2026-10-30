"""Order operations. SQL triggers are the final authority for financial invariants."""
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone
from uuid import uuid4
from .errors import require
from .schema import integer,dec,string,calendar_date,local_to_utc
from .delivery import DELIVERY_FIELDS,delivery_values,notify_order


def own_order(q,user,oid):
    row=q.one('SELECT * FROM dbo.Orders WHERE OrderID=?',(oid,))
    require(row and (user['Role']=='admin' or row['ClientID']==user['ClientID']),'not_found',404)
    return row


def quote(q,route_id,tariff_id,weight):
    route=q.one('SELECT DistanceKm FROM dbo.Routes WHERE RouteID=?',(integer(route_id,'RouteID'),))
    tariff=q.one('SELECT * FROM dbo.Tariffs WHERE TariffID=? AND IsActive=1',(integer(tariff_id,'TariffID'),))
    require(route and tariff,'catalog_missing')
    total=(tariff['BasePrice']+route['DistanceKm']*tariff['PricePerKm']+dec(weight,field='WeightKg')*tariff['PricePerKg']).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
    require(total<Decimal('1000000000000'),'number_range')
    return total


def cargo_values(data):
    require(isinstance(data,dict),'invalid')
    return dict(CargoTypeID=integer(data.get('CargoTypeID'),'CargoTypeID'),Description=string(data.get('Description'),200,'Description'),
                WeightKg=dec(data.get('WeightKg'),field='WeightKg'),VolumeM3=dec(data.get('VolumeM3'),'0.001',3,'VolumeM3'),
                Quantity=integer(data.get('Quantity'),'Quantity'))


def create_order(q,user,data):
    require(isinstance(data,dict) and not set(data)-({'RouteID','TariffID','PickupDate','Notes','items'}|DELIVERY_FIELDS),'unknown_field')
    require(user['Role']=='client','client_only',403)
    items=data.get('items'); require(isinstance(items,list) and 1<=len(items)<=100,'cargo_required')
    items=[cargo_values(item) for item in items]
    route=integer(data.get('RouteID'),'RouteID'); tariff=integer(data.get('TariffID'),'TariffID')
    quote(q,route,tariff,sum(x['WeightKg'] for x in items))
    oid=q.insert('Orders','OrderID',dict(OrderNumber='QZ-'+uuid4().hex[:24].upper(),ClientID=user['ClientID'],RouteID=route,TariffID=tariff,
                  PickupDate=calendar_date(data.get('PickupDate'),'PickupDate'),Notes=string(data.get('Notes'),500,'Notes',True),**delivery_values(data)))
    for item in items: q.insert('CargoItems','CargoItemID',dict(OrderID=oid,**item))
    notify_order(q,oid,'order_created','New','admin')
    return oid


def editable(q,order):
    require(order['Status'] in ('New','Confirmed'),'order_locked',409)
    oid=order['OrderID']
    require(not q.scalar('SELECT TOP 1 PaymentID FROM dbo.Payments WHERE OrderID=?',(oid,)),'order_locked',409)
    require(not q.scalar("SELECT TripID FROM dbo.Trips WHERE OrderID=? AND Status<>'Cancelled'",(oid,)),'order_locked',409)


def change_status(q,user,oid,target):
    order=own_order(q,user,oid)
    if user['Role']=='client': require(order['Status']=='New' and target=='Cancelled','forbidden',403)
    require(target in {'New':('Confirmed','Cancelled'),'Confirmed':('InTransit','Cancelled'),'InTransit':('Delivered',),'Delivered':(),'Cancelled':()}[order['Status']], 'status_transition',409)
    q.execute('EXEC dbo.usp_SetOrderStatus @OrderID=?,@NewStatus=?',(oid,target))
    notify_order(q,oid,'status_changed',target,'admin' if user['Role']=='client' else 'client')


def save_trip(q,user,oid,data):
    order=own_order(q,user,oid)
    require(order['Status']=='Confirmed','trip_confirmed',409)
    status=data.get('Status','Planned'); require(status in ('Planned','Cancelled'),'invalid')
    values=dict(VehicleID=integer(data.get('VehicleID'),'VehicleID'),DriverID=integer(data.get('DriverID'),'DriverID'),
                DepartureAt=local_to_utc(data.get('DepartureAt'),'DepartureAt'),ArrivalAt=local_to_utc(data.get('ArrivalAt'),'ArrivalAt'),Status=status)
    require(values['ArrivalAt']>values['DepartureAt'],'trip_time')
    current=q.one('SELECT TripID,Status FROM dbo.Trips WHERE OrderID=?',(oid,))
    if current:
        require(current['Status'] in ('Planned','Cancelled'),'order_locked',409)
        q.execute('UPDATE dbo.Trips SET VehicleID=?,DriverID=?,DepartureAt=?,ArrivalAt=?,Status=? WHERE TripID=?',(*values.values(),current['TripID']))
        notify_order(q,oid,'trip_updated')
        return current['TripID']
    tid=q.insert('Trips','TripID',dict(OrderID=oid,**values))
    notify_order(q,oid,'trip_updated')
    return tid
