"""Nine-minute Locust matrix, owning only a temporary SQLite server and its children."""
import csv
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time
import urllib.request
import psutil
from sqlmodel import Session
from labs.lab_1_2.database.db import make_engine
from labs.lab_1_2.database.models import CargoItem, Order
from labs.lab_1_2.seed import seed_demo
from datetime import date
from decimal import Decimal

ROOT=Path(__file__).resolve().parents[1]


def main():
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=ROOT/'docs/labs/8/load')
    parser.add_argument('--port',type=int,default=8018)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    host=f'http://127.0.0.1:{args.port}'
    results=[]
    with tempfile.TemporaryDirectory(prefix='qazcargo_load_') as temp:
        database=Path(temp)/'load.db'
        engine=make_engine(database);seed_demo(engine)
        with Session(engine) as session:
            for n in range(197):
                order=Order(OrderNumber=f'LOAD-{n:04}',ClientID=1,RouteID=1,TariffID=1,
                            PickupDate=date.today(),QuotedAmount=Decimal('165150.00'))
                session.add(order);session.flush()
                session.add(CargoItem(OrderID=order.OrderID,CargoTypeID=1,Description='Synthetic load cargo',
                                      WeightKg=Decimal('10.00'),VolumeM3=Decimal('.500'),Quantity=1))
            session.commit()
        engine.dispose()
        env=os.environ.copy();env.update(LAB_DATABASE_PATH=str(database),PYTHONUNBUFFERED='1')
        creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
        with (args.output/'server.log').open('w',encoding='utf-8') as log:
            server=subprocess.Popen([sys.executable,'-m','uvicorn','labs.lab_1_2.main:app','--host','127.0.0.1',
                                     '--port',str(args.port),'--no-access-log'],cwd=ROOT,env=env,stdout=log,stderr=log,
                                    creationflags=creationflags)
            try:
                for _ in range(60):
                    if server.poll() is not None: raise RuntimeError('Isolated API failed to start; inspect server.log')
                    try:
                        with urllib.request.urlopen(host+'/health',timeout=1) as response:
                            if response.status==200: break
                    except OSError: time.sleep(.5)
                else: raise RuntimeError('Isolated API readiness timeout')
                process=psutil.Process(server.pid)
                for users,seconds in ((5,60),(20,120),(50,180),(100,180)):
                    print(f'START users={users} duration={seconds}s',flush=True)
                    prefix=args.output/f'users-{users}'
                    command=[sys.executable,'-m','locust','-f','tools/locustfile.py','--headless','--host',host,
                             '--users',str(users),'--spawn-rate',str(users),'--run-time',str(seconds),
                             '--stop-timeout','10','--only-summary','--csv',str(prefix),'--csv-full-history']
                    samples=[]
                    with prefix.with_suffix('.log').open('w',encoding='utf-8') as output:
                        runner=subprocess.Popen(command,cwd=ROOT,stdout=output,stderr=output,creationflags=creationflags)
                        process.cpu_percent()
                        try:
                            while runner.poll() is None:
                                samples.append({'time':time.time(),'cpu_percent':process.cpu_percent(interval=1),
                                                'rss_mb':process.memory_info().rss/1024**2})
                        finally:
                            if runner.poll() is None: runner.terminate();runner.wait(timeout=15)
                    (args.output/f'users-{users}-resources.json').write_text(json.dumps(samples,indent=2),encoding='utf-8')
                    with Path(str(prefix)+'_stats.csv').open(encoding='utf-8') as handle:
                        total=next(row for row in csv.DictReader(handle) if row['Name']=='Aggregated')
                    record={'users':users,'duration_s':seconds,'requests':int(total['Request Count']),
                            'failures':int(total['Failure Count']),'avg_ms':float(total['Average Response Time']),
                            'p95_ms':float(total['95%']),'p99_ms':float(total['99%']),
                            'rps':float(total['Requests/s']),'exit_code':runner.returncode,
                            'cpu_avg_percent':sum(s['cpu_percent'] for s in samples)/len(samples),
                            'cpu_max_percent':max(s['cpu_percent'] for s in samples),
                            'rss_max_mb':max(s['rss_mb'] for s in samples)}
                    results.append(record)
                    print(json.dumps(record),flush=True)
                    (args.output/'summary.json').write_text(json.dumps({'environment':{
                        'os':platform.platform(),'python':platform.python_version(),'logical_cpus':psutil.cpu_count(),
                        'ram_gb':round(psutil.virtual_memory().total/1024**3,2),'workers':1,'orders':200,
                        'wait_s':[.5,1.5],'cpu_note':'Server process; 100% equals one logical CPU. Load generator shares host.'},
                        'results':results},indent=2),encoding='utf-8')
            finally:
                server.terminate();server.wait(timeout=15)
    return 1 if any(r['exit_code'] or r['failures'] for r in results) else 0


if __name__=='__main__':
    raise SystemExit(main())
