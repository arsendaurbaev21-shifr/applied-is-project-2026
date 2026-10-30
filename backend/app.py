"""Run with python -m backend.app. Bind locally using Waitress, never debug mode."""
from datetime import date,datetime,timedelta,timezone,time
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlsplit
import os
import secrets
from flask import Flask,request,session,jsonify,send_from_directory,redirect
from flask.json.provider import DefaultJSONProvider
from werkzeug.exceptions import HTTPException
from dotenv import load_dotenv
import pyodbc
from . import auth,portal,documents,delivery
from .db import transaction,translate_error
from .errors import AppError

ROOT=Path(__file__).resolve().parent.parent
load_dotenv(ROOT/'.env')


class JSONProvider(DefaultJSONProvider):
    @staticmethod
    def default(value):
        if isinstance(value,Decimal): return format(value,'f')
        if isinstance(value,datetime): return value.replace(tzinfo=value.tzinfo or timezone.utc).isoformat()
        if isinstance(value,date): return value.isoformat()
        if isinstance(value,time): return value.isoformat(timespec='minutes')
        return DefaultJSONProvider.default(value)


def create_app(test_config=None):
    app=Flask(__name__,static_folder=str(ROOT/'web'),static_url_path='/static')
    app.json=JSONProvider(app)
    secret=os.getenv('APP_SECRET','')
    if len(secret)<32: raise RuntimeError('Run FIRST_RUN.bat to create .env with a random APP_SECRET.')
    app.config.update(SECRET_KEY=secret,SESSION_COOKIE_NAME='qazcargo_session',SESSION_COOKIE_HTTPONLY=True,
                      SESSION_COOKIE_SAMESITE='Lax',SESSION_COOKIE_SECURE=os.getenv('COOKIE_SECURE','0')=='1',
                      PERMANENT_SESSION_LIFETIME=timedelta(hours=8),MAX_CONTENT_LENGTH=21*1024*1024,
                      MAX_FORM_MEMORY_SIZE=1024*1024,TRUSTED_HOSTS=['127.0.0.1','localhost'])
    if test_config: app.config.update(test_config)

    @app.before_request
    def csrf_check():
        if request.method in ('POST','PUT','PATCH','DELETE'):
            origin=request.headers.get('Origin')
            if origin and origin!=request.host_url.rstrip('/'): raise AppError('csrf',403)
            if request.headers.get('Sec-Fetch-Site')=='cross-site': raise AppError('csrf',403)
            received=request.headers.get('X-CSRF-Token','')
            if not received or not secrets.compare_digest(received,session.get('csrf','')): raise AppError('csrf',403)

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='same-origin'
        response.headers['X-Frame-Options']='SAMEORIGIN'
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; frame-src 'self' blob:; object-src 'none'; base-uri 'self'; form-action 'self'"
        if request.path.startswith('/api/'): response.headers['Cache-Control']='no-store'
        return response

    @app.errorhandler(AppError)
    def app_error(e): return jsonify(error={'code':e.code,'field':e.field}),e.status

    @app.errorhandler(pyodbc.Error)
    def sql_error(e):
        err=translate_error(e)
        return app_error(err)

    @app.errorhandler(HTTPException)
    def http_error(e): return jsonify(error={'code':{413:'file_size',404:'not_found',405:'method'}.get(e.code,'invalid'),'field':None}),e.code

    @app.errorhandler(Exception)
    def unexpected(e):
        app.logger.error('Unhandled error type: %s',type(e).__name__)
        return jsonify(error={'code':'server_error','field':None}),500

    @app.get('/')
    def home(): return send_from_directory(ROOT/'web','index.html')

    @app.get('/login')
    def login(): return send_from_directory(ROOT/'web','login.html')

    @app.get('/track')
    def track(): return send_from_directory(ROOT/'web','track.html')

    @app.get('/admin')
    @app.get('/customer')
    def cabinet():
        try:
            with transaction() as q: user=auth.current_user(q)
        except AppError as e:
            if e.status==401: return redirect('/login')
            raise
        expected='/admin' if user['Role']=='admin' else '/customer'
        if request.path!=expected: return redirect(expected)
        return send_from_directory(ROOT/'web','admin.html' if user['Role']=='admin' else 'customer.html')

    @app.get('/api/health')
    def health():
        with transaction() as q:
            count=q.scalar("SELECT COUNT(*) FROM sys.tables WHERE schema_id=SCHEMA_ID('dbo')")
            ready=q.scalar("SELECT CASE WHEN OBJECT_ID('dbo.Notifications','U') IS NOT NULL AND COL_LENGTH('dbo.Orders','TrackingCode') IS NOT NULL THEN 1 ELSE 0 END")
            return jsonify(ok=count>=19 and bool(ready) and bool(q.scalar("SELECT OBJECT_ID('dbo.OrderDrafts','U')")),tables=count,database=q.scalar('SELECT DB_NAME()'),schemaVersion=4 if q.scalar("SELECT COL_LENGTH('dbo.Cities','Latitude')") else 3 if q.scalar("SELECT OBJECT_ID('dbo.OrderDrafts','U')") else 2 if ready else 1)

    app.register_blueprint(auth.bp); app.register_blueprint(portal.bp); app.register_blueprint(documents.bp)
    app.register_blueprint(delivery.bp)
    from . import usability
    app.register_blueprint(usability.bp)
    return app


if __name__=='__main__':
    from waitress import serve
    print('QazCargo: http://127.0.0.1:5000  |  Ctrl+C to stop',flush=True)
    serve(create_app(),host='127.0.0.1',port=int(os.getenv('PORT','5000')),threads=8)
