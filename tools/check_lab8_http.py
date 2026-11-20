"""Record real HTTP responses for lab 8 using synthetic data only."""
import argparse
import json
from pathlib import Path
from uuid import uuid4
from datetime import date
import requests


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--url',default='http://127.0.0.1:8000')
    parser.add_argument('--output',type=Path,default=Path('qa/lab8-http.json'))
    args=parser.parse_args()
    base=args.url.rstrip('/')
    session=requests.Session()
    root=session.get(base+'/',timeout=5);root.raise_for_status()
    if root.json().get('data')!='synthetic': raise RuntimeError('Not a synthetic teaching API')
    marker='lab8-http-'+uuid4().hex
    rows=[];owned=None
    def check(name,method,path,expected,**kwargs):
        response=session.request(method,base+path,timeout=10,**kwargs)
        rows.append({'test':name,'method':method,'path':path,'expected':expected,
                     'actual':response.status_code,'body':response.json() if response.content else None})
        if response.status_code!=expected: raise RuntimeError(f'{name}: expected {expected}, got {response.status_code}')
        return response
    try:
        check('GET list','GET','/api/orders?limit=1',200)
        data={'client_id':1,'route_id':1,'tariff_id':1,'pickup_date':date.today().isoformat(),'notes':marker,
              'items':[{'cargo_type_id':1,'description':'Synthetic lab 8 item','weight_kg':'10.00','volume_m3':'.500','quantity':1}]}
        response=check('POST create','POST','/api/orders',201,json=data)
        owned=response.json()['id'];path=f'/api/orders/{owned}'
        check('GET created','GET',path,200)
        data['items'][0]['weight_kg']='20.00'
        check('PUT replace','PUT',path,200,json=data)
        check('Empty object','POST','/api/orders',422,json={})
        check('Malformed JSON','POST','/api/orders',400,data='{broken',headers={'Content-Type':'application/json'})
        data['client_id']=999999
        check('Missing client reference','POST','/api/orders',422,json=data)
        check('Missing order','GET','/api/orders/999999',404)
        check('DELETE owned record','DELETE',path,204)
        check('GET after DELETE','GET',path,404)
        owned=None
    finally:
        if owned is not None:
            response=session.get(base+f'/api/orders/{owned}',timeout=10)
            if response.status_code==200 and response.json().get('notes')==marker:
                session.delete(base+f'/api/orders/{owned}',timeout=10).raise_for_status()
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
        session.close()
    print(f'{len(rows)} real HTTP checks passed; evidence: {args.output}')


if __name__=='__main__':
    main()
