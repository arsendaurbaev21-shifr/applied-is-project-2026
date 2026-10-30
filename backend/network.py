"""Import the audited, offline road snapshot. Never fetch external data during migration."""
import json,math
from decimal import Decimal,ROUND_HALF_UP
from pathlib import Path

DATA=Path(__file__).resolve().parents[1]/'database/data'

def load_network():
    cities=json.loads((DATA/'kz_cities.json').read_text(encoding='utf-8-sig'))['cities']
    network=json.loads((DATA/'kz_road_network.json').read_text(encoding='utf-8'))
    assert len(cities)==90 and len({c['name'] for c in cities})==90
    assert network['cityIds']==[c['sourceId'] for c in cities]
    assert len(network['distances'])==90
    for i,row in enumerate(network['distances']):
        assert len(row)==90
        for j,d in enumerate(row):
            assert isinstance(d,(float,int)) and math.isfinite(d) and (d==0 if i==j else d>0)
    return cities,network

def import_network(q):
    cities,network=load_network()
    routes=[{'a':a['name'],'b':b['name'],'km':str((Decimal(str(network['distances'][i][j]))/1000).quantize(Decimal('.01'),rounding=ROUND_HALF_UP))}
            for i,a in enumerate(cities) for j,b in enumerate(cities) if i!=j]
    # One SQL batch: parameterized RPC scope cannot retain a #temp table across calls.
    q.execute("""SET NOCOUNT ON;
      DECLARE @cities TABLE(name nvarchar(80),region nvarchar(100),latitude decimal(9,6),longitude decimal(9,6),sourceId nvarchar(80),sourceUrl nvarchar(350));
      INSERT @cities SELECT * FROM OPENJSON(?) WITH
        (name nvarchar(80),region nvarchar(100),latitude decimal(9,6),longitude decimal(9,6),sourceId nvarchar(80),sourceUrl nvarchar(350));
      UPDATE c SET Latitude=s.latitude,Longitude=s.longitude,Region=s.region,GeoSourceID=s.sourceId,GeoSourceURL=s.sourceUrl
        FROM dbo.Cities c JOIN @cities s ON s.name=c.Name;
      INSERT dbo.Cities(Name,Latitude,Longitude,Region,GeoSourceID,GeoSourceURL)
        SELECT name,latitude,longitude,region,sourceId,sourceUrl FROM @cities s WHERE NOT EXISTS(SELECT 1 FROM dbo.Cities c WHERE c.Name=s.name);
      DECLARE @routes TABLE(FromCityID int,ToCityID int,DistanceKm decimal(10,2));
      INSERT @routes SELECT a.CityID,b.CityID,s.km FROM OPENJSON(?) WITH(a nvarchar(80),b nvarchar(80),km decimal(10,2)) s
        JOIN dbo.Cities a ON a.Name=s.a JOIN dbo.Cities b ON b.Name=s.b;
      IF (SELECT COUNT(*) FROM @routes)<>8010 THROW 51000,'Incomplete road network',1;
      DECLARE @source nvarchar(100)=?,@dated date=CONVERT(date,?);
      UPDATE r SET DistanceKm=s.DistanceKm,DistanceSource=@source,DistanceUpdatedAt=@dated FROM dbo.Routes r
        JOIN @routes s ON s.FromCityID=r.FromCityID AND s.ToCityID=r.ToCityID;
      INSERT dbo.Routes(FromCityID,ToCityID,DistanceKm,DistanceSource,DistanceUpdatedAt)
        SELECT s.FromCityID,s.ToCityID,s.DistanceKm,@source,@dated FROM @routes s
        WHERE NOT EXISTS(SELECT 1 FROM dbo.Routes r WHERE r.FromCityID=s.FromCityID AND r.ToCityID=s.ToCityID);
      """,(json.dumps(cities,ensure_ascii=False),json.dumps(routes,ensure_ascii=False),network['provider']+' · driving',network['fetchedAt'][:10]))
    return {'cities':90,'routes':8010,'fetchedAt':network['fetchedAt']}
