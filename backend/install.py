"""Interactive installer; only an exact typed allowlisted name authorizes reset."""
from pathlib import Path
from datetime import datetime,timezone
import os
import re
import secrets
import sys
from dotenv import load_dotenv
from .db import connect

ROOT=Path(__file__).resolve().parent.parent
ALLOWED_RESET={'QazCargo','QazCargo13'}


def consume(cur):
    while cur.nextset(): pass


def run_script(connection,path):
    for batch in re.split(r'^\s*GO\s*(?:--[^\n]*)?$',path.read_text(encoding='utf-8-sig'),flags=re.M|re.I):
        if batch.strip():
            cur=connection.cursor()
            try: cur.execute(batch); consume(cur)
            finally: cur.close()
    # An exception aborts the loop, never continuing into later GO batches.


def backup(connection,name):
    if name not in ALLOWED_RESET: raise ValueError('Only QazCargo or QazCargo13 is allowed.')
    cur=connection.cursor()
    try:
        folder=cur.execute("SELECT CONVERT(nvarchar(4000),SERVERPROPERTY('InstanceDefaultBackupPath'))").fetchone()[0]
        if not folder: raise RuntimeError('SQL Server backup path is unavailable.')
        path=folder.rstrip('\\/')+'\\'+name+'_'+datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')+'_'+secrets.token_hex(6)+'.bak'
        cur.execute(f'BACKUP DATABASE [{name}] TO DISK=? WITH COPY_ONLY,CHECKSUM',(path,)); consume(cur)
        cur.execute('RESTORE VERIFYONLY FROM DISK=? WITH CHECKSUM',(path,)); consume(cur)
        with (ROOT/'BACKUP_LOCATIONS.txt').open('a',encoding='utf-8') as log: log.write(path+'\n')
        print('Verified backup:',path,flush=True)
        return path
    finally: cur.close()


def backup_and_drop(connection,name,confirmation):
    if name not in ALLOWED_RESET or confirmation!=name: raise ValueError('Exact allowed database name required.')
    cur=connection.cursor(); exclusive=False
    try:
        cur.execute(f'ALTER DATABASE [{name}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE'); consume(cur); exclusive=True
        path=backup(connection,name)  # BACKUP and VERIFYONLY must both succeed.
        cur.execute(f'DROP DATABASE [{name}]'); consume(cur); exclusive=False
        return path
    finally:
        if exclusive:
            cur.execute(f'ALTER DATABASE [{name}] SET MULTI_USER WITH ROLLBACK IMMEDIATE'); consume(cur)
        cur.close()


def prepare_env(server=None):
    path=ROOT/'.env'
    if not path.exists():
        server=server or input('SQL Server name from SSMS [localhost]: ').strip() or 'localhost'
        if any(x in server for x in '\r\n#\"\''): raise ValueError('Invalid server name.')
        content=(ROOT/'.env.example').read_text(encoding='utf-8').replace('DB_SERVER=localhost','DB_SERVER='+server)
        content=content.replace('APP_SECRET=GENERATED_BY_INSTALLER','APP_SECRET='+secrets.token_urlsafe(48))
        path.write_text(content,encoding='utf-8')
    load_dotenv(path,override=True)
    if os.getenv('DB_DATABASE')!='QazCargo': raise RuntimeError('Use DB_DATABASE=QazCargo.')
    if len(os.getenv('APP_SECRET',''))<32 or os.getenv('APP_SECRET')=='GENERATED_BY_INSTALLER': raise RuntimeError('APP_SECRET must be a random 32+ character value.')


def main():
    prepare_env()
    with connect('master',True) as conn:
        exists=conn.cursor().execute("SELECT DB_ID(N'QazCargo')").fetchone()[0]
        if exists:
            print('QazCargo already exists. Enter keeps it; RESET requests a verified-backup reset.')
            if input('Choice: ').strip()!='RESET':
                print('Existing database preserved. Run UPDATE_DATABASE.bat for updates, then START.bat or SET_ADMIN.bat.'); return
            print('All QazCargo data will be replaced. No automatic migration. Stop the website first.')
            answer=input('Type the exact database name QazCargo: ').strip()
            if answer!='QazCargo': print('Cancelled. Nothing deleted.'); return
            backup_and_drop(conn,'QazCargo',answer)
        print('Creating QazCargo. Existing QazCargo13 is preserved.')
        run_script(conn,ROOT/'database/01_create_database.sql')
        run_script(conn,ROOT/'database/02_seed_catalogs.sql')
        run_script(conn,ROOT/'database/04_delivery_tracking_notifications.sql')
        run_script(conn,ROOT/'database/05_order_drafts.sql')
        run_script(conn,ROOT/'database/06_city_network.sql')
    from .network import import_network
    from .db import transaction
    with transaction(True) as q:import_network(q)
    from .manage import admin_console
    admin_console()
    print('READY. Run START.bat and open http://127.0.0.1:5000')


if __name__=='__main__':
    try: main()
    except (EOFError,KeyboardInterrupt): print('Installation cancelled. Existing data preserved.'); sys.exit(1)
    except Exception as error:
        print('Installation failed:',str(error)); print('Do not remove backups. Check SQL Server, ODBC and .env.'); sys.exit(1)
