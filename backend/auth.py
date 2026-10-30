"""Session revocation is checked against SQL on every protected request."""
from datetime import datetime, timedelta, timezone
import secrets
from functools import wraps
from flask import Blueprint, request, session, g, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from .db import transaction
from .errors import require, AppError
from .schema import string, email, password

bp=Blueprint('auth',__name__,url_prefix='/api/auth')
PUBLIC_USER='UserID,Email,FullName,Role,ClientID,IsActive,AuthVersion'
DUMMY_HASH=generate_password_hash(secrets.token_urlsafe(32),method='scrypt')


def current_user(q):
    user=q.one(f'SELECT {PUBLIC_USER} FROM dbo.Users WHERE UserID=?',(session.get('uid',0),))
    if not user or not user['IsActive'] or user['AuthVersion']!=session.get('version'):
        session.pop('uid',None)
        session.pop('version',None)
        raise AppError('login_required',401)
    return user


def protected(admin=False, write=False):
    def decorate(fn):
        @wraps(fn)
        def wrapper(*args,**kwargs):
            with transaction(write) as q:
                g.q=q
                g.user=current_user(q)
                require(not admin or g.user['Role']=='admin','forbidden',403)
                return fn(*args,**kwargs)
        return wrapper
    return decorate


def establish(user):
    session.clear()
    session.update(uid=user['UserID'],version=user['AuthVersion'],csrf=secrets.token_urlsafe(32))
    session.permanent=True


@bp.get('/session')
def info():
    session.setdefault('csrf',secrets.token_urlsafe(32))
    user=None
    if session.get('uid'):
        with transaction() as q:
            try: user=current_user(q)
            except AppError: pass
    return jsonify(user=user,csrf=session['csrf'])


@bp.post('/register')
def register():
    data=request.get_json()
    require(isinstance(data,dict) and not set(data)-{'FullName','Email','Phone','Address','Password'},'unknown_field')
    name=string(data.get('FullName'),120,'FullName'); mail=email(data.get('Email'))
    phone=string(data.get('Phone'),30,'Phone'); address=string(data.get('Address'),250,'Address',True)
    hashed=generate_password_hash(password(data.get('Password')),method='scrypt')
    with transaction(True) as q:
        require(not q.scalar('SELECT UserID FROM dbo.Users WHERE Email=?',(mail,)),'duplicate',409)
        cid=q.insert('Clients','ClientID',dict(Name=name,Phone=phone,Email=mail,Address=address))
        uid=q.insert('Users','UserID',dict(Email=mail,FullName=name,PasswordHash=hashed,Role='client',ClientID=cid))
        user=q.one(f'SELECT {PUBLIC_USER} FROM dbo.Users WHERE UserID=?',(uid,))
    establish(user)
    return jsonify(user=user,csrf=session['csrf']),201


@bp.post('/login')
def login():
    data=request.get_json()
    require(isinstance(data,dict),'invalid')
    mail=email(data.get('Email')); raw=data.get('Password','')
    require(isinstance(raw,str) and len(raw)<=128,'login_failed',401)
    success=False
    with transaction(True) as q:
        user=q.one('SELECT * FROM dbo.Users WITH(UPDLOCK,HOLDLOCK) WHERE Email=?',(mail,))
        now=datetime.now(timezone.utc).replace(tzinfo=None)
        matches=check_password_hash(user['PasswordHash'] if user else DUMMY_HASH,raw)
        if user and user['IsActive'] and not (user['LockedUntil'] and user['LockedUntil']>now):
            if matches:
                q.execute('UPDATE dbo.Users SET FailedAttempts=0,LockedUntil=NULL WHERE UserID=?',(user['UserID'],))
                success=True
            else:
                attempts=(0 if user['LockedUntil'] and user['LockedUntil']<=now else user['FailedAttempts'])+1
                q.execute('UPDATE dbo.Users SET FailedAttempts=?,LockedUntil=? WHERE UserID=?',
                          (attempts,now+timedelta(minutes=10) if attempts>=5 else None,user['UserID']))
    # The failed-attempt update commits before the HTTP error is raised.
    require(success,'login_failed',401)
    establish(user)
    return jsonify(user={k:user[k] for k in PUBLIC_USER.split(',')},csrf=session['csrf'])


@bp.post('/logout')
def logout():
    session.clear()
    return jsonify(ok=True)


@bp.post('/password')
@protected(write=True)
def change_password():
    data=request.get_json(); require(isinstance(data,dict),'invalid')
    row=g.q.one('SELECT PasswordHash FROM dbo.Users WHERE UserID=?',(g.user['UserID'],))
    require(check_password_hash(row['PasswordHash'],str(data.get('CurrentPassword',''))),'current_password')
    hashed=generate_password_hash(password(data.get('Password')),method='scrypt')
    g.q.execute('UPDATE dbo.Users SET PasswordHash=?,AuthVersion=AuthVersion+1,FailedAttempts=0,LockedUntil=NULL WHERE UserID=?',(hashed,g.user['UserID']))
    session['version']=g.user['AuthVersion']+1
    return jsonify(ok=True)


@bp.get('/users')
@protected(admin=True)
def users():
    return jsonify(rows=g.q.rows('SELECT UserID,Email,FullName,Role,IsActive,CreatedAt FROM dbo.Users ORDER BY UserID DESC'))


@bp.patch('/users/<int:uid>')
@protected(admin=True,write=True)
def block(uid):
    data=request.get_json(); require(isinstance(data,dict) and type(data.get('IsActive')) is bool,'invalid')
    row=g.q.one("SELECT UserID FROM dbo.Users WHERE UserID=? AND Role='client'",(uid,))
    require(row,'not_found',404)
    g.q.execute('UPDATE dbo.Users SET IsActive=?,AuthVersion=AuthVersion+1 WHERE UserID=?',(data['IsActive'],uid))
    return jsonify(ok=True)
