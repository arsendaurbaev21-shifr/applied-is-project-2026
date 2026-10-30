"""Run the catalogue expansion after legacy price tests in the disposable DB."""
import hashlib,json
from decimal import Decimal,ROUND_HALF_UP
from backend.network import load_network,import_network,DATA
from backend.db import transaction
from tools.build_road_network import validate
from conftest import new_order

def test_complete_sourced_matrix():
    cities,network=load_network()
    raw=(DATA/'osrm_table_response.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==network['responseSha256']
    validate(cities,json.loads(raw))
    assert network['distances']==json.loads(raw)['distances']
    assert len({c['kato'] for c in cities})==90
    assert len({c['region'] for c in cities})==20
    assert all(c['sourceUrl'].startswith('https://') for c in cities)
    assert any(network['distances'][i][j]!=network['distances'][j][i] for i in range(90) for j in range(i))

def test_network_import_preserves_orders_ids_and_custom_records(actors):
    admin,client,_=actors;oid=new_order(client)
    with transaction(True) as q:
        old_orders=q.rows('SELECT * FROM dbo.Orders ORDER BY OrderID')
        old_users=q.rows('SELECT * FROM dbo.Users ORDER BY UserID')
        old_routes=q.rows('SELECT RouteID,FromCityID,ToCityID FROM dbo.Routes ORDER BY RouteID')
        custom=q.insert('Cities','CityID',{'Name':'Network test custom location'})
        custom_route=q.insert('Routes','RouteID',{'FromCityID':custom,'ToCityID':1,'DistanceKm':'10'})
        result=import_network(q)
        assert result['routes']==8010
        assert q.scalar('SELECT COUNT(*) FROM dbo.Cities WHERE Latitude IS NOT NULL')==90
        assert q.scalar('SELECT COUNT(*) FROM dbo.Routes WHERE DistanceSource IS NOT NULL')==8010
        assert q.rows('SELECT * FROM dbo.Orders ORDER BY OrderID')==old_orders
        assert q.rows('SELECT * FROM dbo.Users ORDER BY UserID')==old_users
        assert q.scalar('SELECT DistanceKm FROM dbo.Routes WHERE RouteID=?',(custom_route,))==10
        for r in old_routes:
            assert q.one('SELECT RouteID,FromCityID,ToCityID FROM dbo.Routes WHERE RouteID=?',(r['RouteID'],))==r
        counts=(q.scalar('SELECT COUNT(*) FROM dbo.Cities'),q.scalar('SELECT COUNT(*) FROM dbo.Routes'))
        import_network(q)
        assert counts==(q.scalar('SELECT COUNT(*) FROM dbo.Cities'),q.scalar('SELECT COUNT(*) FROM dbo.Routes'))
    cities,network=load_network();i=next(i for i,c in enumerate(cities) if c['name']=='Астана');j=next(i for i,c in enumerate(cities) if c['name']=='Шымкент')
    km=(Decimal(str(network['distances'][i][j]))/1000).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
    quote=client.get('/public/quote?RouteID=1&TariffID=1&WeightKg=100.25').json
    assert Decimal(quote['amount'])==Decimal(15000)+km*120+Decimal('100.25')*15
    assert admin.request('PUT','/catalogs/Routes/'+str(custom_route),{'FromCityID':custom,'ToCityID':1,'DistanceKm':'11'}).status_code==200
