"""Create a portable, credential-free delivery ZIP using only stdlib."""
from pathlib import Path
import hashlib,json,zipfile

ROOT=Path(__file__).resolve().parents[1]
SKIP={'.venv','venv','.vs','.pytest_cache','__pycache__','qa','node_modules','.git'}
EXACT={'.env','BACKUP_LOCATIONS.txt','QazCargo_Full.zip','PACKAGE_MANIFEST.json','SHA256SUMS.txt','SHARE_LINK.txt'}
RETIRED={'docs/diagrams/accounts.png','docs/diagrams/orders.png','docs/diagrams/transport.png'}
def included(path):
    rel=path.relative_to(ROOT)
    return (rel.as_posix() not in RETIRED and not any(p in SKIP for p in rel.parts)
            and path.name not in EXACT
            and not (path.name.startswith('.env.') and path.name != '.env.example')
            and not any(part in path.name.lower() for part in ('.db-', '.sqlite'))
            and path.suffix.lower() not in {'.pyc','.pyo','.bak','.user','.db','.zip','.log'})

def main():
    files=sorted(p for p in ROOT.rglob('*') if p.is_file() and included(p))
    # Fail closed if sensitive development artifacts accidentally change location.
    assert not any('ui_credentials' in str(p) for p in files)
    manifest={p.relative_to(ROOT).as_posix():{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files}
    target=ROOT/'QazCargo_Full.zip'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=7) as z:
        for p in files:z.write(p,'QazCargo/'+p.relative_to(ROOT).as_posix())
        z.writestr('QazCargo/PACKAGE_MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None
        for rel,expected in manifest.items():
            assert hashlib.sha256(z.read('QazCargo/'+rel)).hexdigest()==expected['sha256'],rel
    (ROOT/'PACKAGE_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'SHA256SUMS.txt').write_text(hashlib.sha256(target.read_bytes()).hexdigest()+'  '+target.name+'\n',encoding='ascii')
    print(f'ZIP verified: {len(files)} files, {target.stat().st_size:,} bytes: {target}')

if __name__=='__main__':main()
