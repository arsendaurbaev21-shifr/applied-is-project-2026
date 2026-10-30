"""Download one OSRM distance matrix for the sourced city centres. No invented fallback.
The demo request is for this educational local project, below its 100-location limit.
Run explicitly to refresh; normal site use reads the bundled snapshot without HTTP calls.
"""
import hashlib,json,math,sys,urllib.request
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]

def great_circle(a,b):
    p1,p2=map(math.radians,(a['latitude'],b['latitude']))
    dl=math.radians(b['longitude']-a['longitude'])
    return 6371008.8*2*math.asin(min(1,math.sqrt(math.sin((p2-p1)/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2)))

def validate(cities,data):
    n=len(cities)
    assert n==90 and len({c['sourceId'] for c in cities})==n
    assert data['code']=='Ok' and len(data['distances'])==n
    assert len(data['sources'])==n and len(data['destinations'])==n
    assert not data.get('fallback_speed_cells'), 'Estimated cells are not accepted'
    for i,a in enumerate(cities):
        assert len(data['distances'][i])==n
        assert data['sources'][i]['distance']<5000,(a['name'],'road snap too far')
        for j,b in enumerate(cities):
            d=data['distances'][i][j]
            assert isinstance(d,(int,float)) and math.isfinite(d),(a['name'],b['name'],'missing road')
            if i==j:assert d==0
            else:
                assert 0<d<15000000
                assert d+data['sources'][i]['distance']+data['destinations'][j]['distance']>=great_circle(a,b)*.99,(a['name'],b['name'],'distance too short')

def main():
    source=json.loads((ROOT/'database/data/kz_cities.json').read_text(encoding='utf-8-sig'))
    cities=source['cities'];coords=';'.join(f"{c['longitude']},{c['latitude']}" for c in cities)
    url='https://router.project-osrm.org/table/v1/driving/'+coords+'?annotations=distance,duration'
    req=urllib.request.Request(url,headers={'User-Agent':'QazCargo-Local-Educational-Map/1.0'})
    with urllib.request.urlopen(req,timeout=55) as r:raw=r.read()
    data=json.loads(raw);validate(cities,data)
    fetched=datetime.now(timezone.utc).isoformat()
    output={'fetchedAt':fetched,'provider':'OSRM / OpenStreetMap','profile':'driving','units':'metres',
      'requestUrl':url,'responseSha256':hashlib.sha256(raw).hexdigest(),'cityIds':[c['sourceId'] for c in cities],
      'distances':data['distances'],'durationsSeconds':data['durations'],
      'snappedCentres':[{'location':p['location'],'offsetMetres':p['distance']} for p in data['sources']],
      'license':'ODbL 1.0','licenseUrl':'https://opendatacommons.org/licenses/odbl/1-0/',
      'sourceUrl':'https://www.openstreetmap.org/copyright','engineUrl':'https://project-osrm.org/'}
    (ROOT/'database/data/kz_road_network.json').write_text(json.dumps(output,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    (ROOT/'database/data/osrm_table_response.json').write_bytes(raw)
    print('Verified 90 cities and 8010 directed road distances; maximum snap',round(max(p['distance'] for p in data['sources'])),'m')

if __name__=='__main__':main()
