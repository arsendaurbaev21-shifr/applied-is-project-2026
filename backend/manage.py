"""Local console administrator creation/recovery; passwords never go into shell arguments."""
import argparse
from getpass import getpass
from werkzeug.security import generate_password_hash
from .install import prepare_env,backup
from .db import transaction,connect
from .schema import email,password,string
from .errors import AppError


def prompt_value(prompt, validator, message, hidden=False):
    while True:
        try:
            return validator((getpass if hidden else input)(prompt))
        except AppError:
            print(message)


def admin_console():
    print('Әкімші аккаунтын жасау немесе қалпына келтіру. Пароль экранда көрінбейді.')
    mail=prompt_value('Әкімші email: ',email,'Email қате. @ белгісі бар толық адрес енгізіңіз, мысалы: name@example.com')
    name=prompt_value('Аты-жөніңіз: ',lambda value:string(value,120),'Аты-жөніңіз бос болмауы және 120 таңбадан аспауы керек.')
    while True:
        secret=prompt_value('Пароль (10–128 таңба): ',password,'Пароль ұзындығы 10–128 таңба болуы керек.',hidden=True)
        if secret==getpass('Парольді қайталаңыз: '): break
        print('Парольдер сәйкес келмейді. Қайта енгізіңіз.')
    hashed=generate_password_hash(secret,method='scrypt')
    with transaction(True) as q:
        user=q.one('SELECT UserID,Role FROM dbo.Users WHERE Email=?',(mail,))
        if user:
            if user['Role']!='admin': raise ValueError('Бұл email клиент аккаунтында қолданылған. Әкімші үшін басқа email енгізіңіз.')
            q.execute('UPDATE dbo.Users SET FullName=?,PasswordHash=?,IsActive=1,AuthVersion=AuthVersion+1,FailedAttempts=0,LockedUntil=NULL WHERE UserID=?',(name,hashed,user['UserID']))
        else: q.insert('Users','UserID',dict(Email=mail,FullName=name,PasswordHash=hashed,Role='admin',ClientID=None))
    print('Әкімші аккаунты дайын:',mail)
    print('Кіру: http://127.0.0.1:5000/login?role=admin')


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('command',nargs='?',choices=['admin','backup'],default='admin'); args=parser.parse_args()
    try:
        prepare_env()
        if args.command=='admin': admin_console()
        else:
            with connect('master',True) as conn: backup(conn,'QazCargo')
    except (KeyboardInterrupt,EOFError):
        print('\nЕнгізу тоқтатылды. Қайта бастау үшін SET_ADMIN.bat ашыңыз.')
        return 130
    except (AppError,ValueError) as error:
        if isinstance(error,AppError) and error.code=='db_unavailable':
            print('SQL Server-ге қосылу мүмкін болмады. SQL қызметін және .env баптауын тексеріңіз.')
        else: print('Операция аяқталмады:',str(error))
        return 1
    return 0


if __name__=='__main__':
    raise SystemExit(main())
