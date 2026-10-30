"""Start one temporary HTTPS link; Ctrl+C stops only the children we create."""
from pathlib import Path
import hashlib
import json
import os
import queue
import re
import socket
import subprocess
import sys
import threading
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
RUNTIME=ROOT/'qa'/'share'
VERSION='2026.10.1'
SHA256='4d2490e74082c5d48dbfedaf92576fa5bd1702379ab88eb7faa0cfbe8dc891b6'
DOWNLOAD=f'https://github.com/cloudflare/cloudflared/releases/download/{VERSION}/cloudflared-windows-amd64.exe'
EXE=RUNTIME/'cloudflared.exe'


def cloudflared():
    RUNTIME.mkdir(parents=True,exist_ok=True)
    if EXE.is_file() and hashlib.sha256(EXE.read_bytes()).hexdigest()==SHA256:
        return EXE
    print('Downloading the official Cloudflare tunnel client...',flush=True)
    partial=RUNTIME/'cloudflared.download'
    with urllib.request.urlopen(DOWNLOAD,timeout=90) as response,partial.open('wb') as output:
        while chunk:=response.read(1024*1024): output.write(chunk)
    if hashlib.sha256(partial.read_bytes()).hexdigest()!=SHA256:
        raise RuntimeError('Cloudflare download checksum mismatch; executable was not started.')
    partial.replace(EXE)
    return EXE


def stop_owned(process):
    if process and process.poll() is None:
        process.terminate()
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill();process.wait(timeout=5)


def main():
    if os.name!='nt': raise RuntimeError('This launcher is for Windows x64.')
    with socket.socket() as probe:
        try:probe.bind(('127.0.0.1',5002))
        except OSError:raise RuntimeError('Port 5002 is occupied. An existing share may still be running.')
    tunnel=server=None
    try:
        executable=cloudflared()
        tunnel=subprocess.Popen([str(executable),'tunnel','--no-autoupdate','--protocol','http2','--url','http://127.0.0.1:5002'],
            cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',
            creationflags=subprocess.CREATE_NO_WINDOW)
        lines=queue.Queue()
        def collect():
            with (RUNTIME/'cloudflared.log').open('w',encoding='utf-8') as logfile:
                for line in tunnel.stdout:
                    logfile.write(line);logfile.flush();lines.put(line)
            lines.put(None)
        threading.Thread(target=collect,daemon=True).start()
        deadline=time.monotonic()+120
        address=None
        while time.monotonic()<deadline:
            try:line=lines.get(timeout=1)
            except queue.Empty:
                if tunnel.poll() is not None:break
                continue
            if line is None:break
            match=re.search(r'https://([a-z0-9]+(?:-[a-z0-9]+)*\.trycloudflare\.com)',line)
            if match:address=match.group(0);hostname=match.group(1);break
        if not address:raise RuntimeError('Cloudflare did not issue a link. See qa/share/cloudflared.log.')
        server=subprocess.Popen([sys.executable,'-m','backend.share','--hostname',hostname],cwd=ROOT,
                                creationflags=subprocess.CREATE_NO_WINDOW)
        for _ in range(40):
            if server.poll() is not None:raise RuntimeError('The share server stopped before startup.')
            try:
                with socket.create_connection(('127.0.0.1',5002),timeout=.5):break
            except OSError:time.sleep(.25)
        else:raise RuntimeError('The share listener did not start.')
        (ROOT/'SHARE_LINK.txt').write_text(
            'QazCargo — уақытша сілтеме\n'+address+'\n\n'
            'Компьютер, интернет және осы SHARE_START терезесі қосулы тұрсын.\n'
            'Тіркелу → клиент кабинеті. Тоқтату: осы терезеде Ctrl+C.\n'
            'Тоқтағаннан кейін бұл сілтеме жұмыс істемейді. Қайта қосқанда жаңа сілтеме беріледі.\n',encoding='utf-8')
        (RUNTIME/'state.json').write_text(json.dumps({'url':address,'launcher_pid':os.getpid(),
            'tunnel_pid':tunnel.pid,'server_pid':server.pid},indent=2),encoding='utf-8')
        print('\nQazCargo temporary link: '+address,flush=True)
        print('Keep this process and the computer running. Ctrl+C stops sharing.',flush=True)
        while tunnel.poll() is None and server.poll() is None:time.sleep(1)
        raise RuntimeError('The tunnel or share server stopped. Start again to obtain a new link.')
    except KeyboardInterrupt:
        print('\nTemporary sharing stopped.',flush=True)
    finally:
        stop_owned(tunnel)
        stop_owned(server)


if __name__=='__main__':
    try:main()
    except Exception as error:
        print('Share error:',str(error),flush=True)
        raise SystemExit(1)
