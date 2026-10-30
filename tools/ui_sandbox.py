"""Optional developer UI sandbox at port 5001. Never seeds the user's QazCargo DB."""
import json,os,re,secrets,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app import create_app
from backend.db import connect,transaction
from backend.install import ROOT,consume
from werkzeug.security import generate_password_hash
from waitress import serve

name='QazCargo_UI_'+secrets.token_hex(6)
conn=connect('master',True);created=False
try:
    for filename in ['01_create_database.sql','02_seed_catalogs.sql','04_delivery_tracking_notifications.sql','05_order_drafts.sql','06_city_network.sql']:
        sql=(ROOT/'database'/filename).read_text(encoding='utf-8-sig').replace("DB_ID(N'QazCargo')",f"DB_ID(N'{name}')").replace('CREATE DATABASE QazCargo',f'CREATE DATABASE [{name}]').replace('USE QazCargo;',f'USE [{name}];')
        for batch in re.split(r'^\s*GO\s*(?:--[^\n]*)?$',sql,flags=re.M|re.I):
            if batch.strip():
                cur=conn.cursor();cur.execute(batch);consume(cur);cur.close()
                if conn.cursor().execute('SELECT DB_ID(?)',(name,)).fetchone()[0]:created=True
    os.environ['DB_DATABASE']=name
    from backend.network import import_network
    with transaction(True) as q:import_network(q)
    password=secrets.token_urlsafe(20)
    with transaction(True) as q:
        q.insert('Users','UserID',dict(Email='admin@ui.test',FullName='Әкімші · сынақ',Role='admin',ClientID=None,PasswordHash=generate_password_hash(password)))
        cid=q.insert('Clients','ClientID',dict(Name='Клиент · сынақ',Phone='Оқу үлгісі',Email='client@ui.test'))
        q.insert('Users','UserID',dict(Email='client@ui.test',FullName='Клиент · сынақ',Role='client',ClientID=cid,PasswordHash=generate_password_hash(password)))
    qa=ROOT/'qa';qa.mkdir(exist_ok=True)
    (qa/'ui_credentials.json').write_text(json.dumps({'admin':'admin@ui.test','client':'client@ui.test','password':password}),encoding='utf-8')
    print('Disposable UI sandbox: http://127.0.0.1:5001',flush=True)
    serve(create_app({'SECRET_KEY':secrets.token_urlsafe(48),'SESSION_COOKIE_NAME':'qazcargo_qa_session'}),host='127.0.0.1',port=5001,threads=6)
finally:
    conn.close()
    if created:
        assert re.fullmatch(r'QazCargo_UI_[0-9a-f]{12}',name)
        cleanup=connect('master',True)
        cur=cleanup.cursor();cur.execute(f'ALTER DATABASE [{name}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE');consume(cur)
        cur.execute(f'DROP DATABASE [{name}]');consume(cur);cur.close();cleanup.close()
    credential_file=ROOT/'qa/ui_credentials.json'
    if credential_file.exists():credential_file.unlink()
