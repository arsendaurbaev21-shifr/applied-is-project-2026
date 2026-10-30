"""Apply additive migrations in one transaction after a verified backup."""
from .install import ROOT,run_script,backup,prepare_env
from .db import connect,DB
from .network import import_network

def apply_migrations(connection):
    for name in ('04_delivery_tracking_notifications.sql','05_order_drafts.sql','06_city_network.sql'):
        run_script(connection,ROOT/'database'/name)

def main():
    prepare_env()
    with connect('master',True) as c:backup(c,'QazCargo')
    c=connect()
    try:
        apply_migrations(c)
        import_network(DB(c))
        c.commit()
        print('QazCargo update complete. Existing accounts, orders and files preserved.')
    except Exception:
        c.rollback();raise
    finally:c.close()

if __name__=='__main__':main()
