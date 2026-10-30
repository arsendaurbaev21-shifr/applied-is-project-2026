"""One connection/transaction per operation. Only SQL Server stores application data."""
import os
from contextlib import contextmanager
import pyodbc
from .errors import AppError


def connection_string(database=None):
    values = {'DRIVER': os.getenv('DB_DRIVER', 'ODBC Driver 18 for SQL Server'),
              'SERVER': os.getenv('DB_SERVER', 'localhost'),
              'DATABASE': database or os.getenv('DB_DATABASE', 'QazCargo'),
              'Encrypt': 'yes', 'TrustServerCertificate': os.getenv('DB_TRUST_CERTIFICATE', 'yes')}
    if os.getenv('DB_AUTH', 'windows') == 'windows':
        values['Trusted_Connection'] = 'yes'
    else:
        values.update(UID=os.environ['DB_USER'], PWD=os.environ['DB_PASSWORD'])
    return ';'.join(k+'={'+str(v).replace('}', '}}')+'}' for k,v in values.items())+';'


def connect(database=None, autocommit=False):
    try:
        return pyodbc.connect(connection_string(database), timeout=8, autocommit=autocommit)
    except pyodbc.Error:
        raise AppError('db_unavailable', 503) from None


class DB:
    def __init__(self, conn): self.conn = conn

    def rows(self, sql, params=()):
        cur = self.conn.cursor()
        try:
            cur.execute(sql, tuple(params))
            while cur.description is None:
                if not cur.nextset(): return []
            names = [c[0] for c in cur.description]
            result = [dict(zip(names, row)) for row in cur.fetchall()]
            while cur.nextset(): pass
            return result
        finally: cur.close()

    def one(self, sql, params=()):
        rows = self.rows(sql, params)
        return rows[0] if rows else None

    def scalar(self, sql, params=()):
        row = self.one(sql, params)
        return next(iter(row.values())) if row else None

    def execute(self, sql, params=()): self.rows(sql, params)

    def insert(self, table, pk, values):
        # All identifiers are internal constants or validated catalog metadata.
        names = ','.join('['+k+']' for k in values)
        return self.scalar(f'SET NOCOUNT ON; DECLARE @ids TABLE(ID int); INSERT dbo.[{table}] ({names}) '
                           f'OUTPUT inserted.[{pk}] INTO @ids VALUES ({",".join("?" for _ in values)}); SELECT ID FROM @ids;', values.values())


@contextmanager
def transaction(write=False):
    conn = connect()
    q = DB(conn)
    try:
        q.execute('SET NOCOUNT ON; SET XACT_ABORT ON; SET LOCK_TIMEOUT 10000;')
        q.execute("EXEC sys.sp_set_session_context @key=N'QazCargo.TimeZone', @value=?", (os.getenv('SQL_TIMEZONE', 'Qyzylorda Standard Time'),))
        if write:
            q.execute('SET TRANSACTION ISOLATION LEVEL SERIALIZABLE; IF @@TRANCOUNT=0 BEGIN TRANSACTION;')
            lock = q.scalar("DECLARE @r int; EXEC @r=sys.sp_getapplock @Resource=N'QazCargo.ApiWrite',@LockMode=N'Exclusive',@LockOwner=N'Transaction',@LockTimeout=10000; SELECT @r;")
            if lock is None or lock < 0: raise AppError('busy', 409)
        yield q
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally: conn.close()


def translate_error(error):
    detail = ' '.join(map(str, error.args))
    import re
    match = re.search(r'\((510\d\d)\)', detail)
    if match: return AppError('sql_'+match[1], 409)
    if any(x in detail for x in ('2601', '2627')): return AppError('duplicate', 409)
    if '547' in detail: return AppError('linked_or_invalid', 409)
    if any(x in detail for x in ('1205', '1222')): return AppError('busy', 409)
    if any(x in detail for x in ('8115', '22003')): return AppError('number_range')
    return AppError('db_operation', 503)
