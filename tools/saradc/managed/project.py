"""Atomic persistence and project paths used by the existing managed engine."""
import hashlib, json, os, subprocess, time, uuid
from datetime import datetime, timezone
from pathlib import Path
import yaml
ROOT = Path(__file__).resolve().parents[3]

def remote_host():
    return load(ROOT / 'site.local.yaml')['roots']['remote_host']

def now():return datetime.now(timezone.utc).isoformat(timespec='seconds')

def load(p):
    with Path(p).open(encoding='utf-8-sig') as f:
        return json.load(f) if str(p).endswith('.json') else yaml.safe_load(f)

def save(p,data):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    if p.suffix=='.json':text=json.dumps(data,ensure_ascii=False,indent=2)+'\n'
    else:text=yaml.safe_dump(data,allow_unicode=True,sort_keys=False,width=120)
    temporary=p.with_name(p.name+'.tmp-'+uuid.uuid4().hex)
    try:
        with temporary.open('x',encoding='utf-8',newline='\n') as f:
            f.write(text);f.flush();os.fsync(f.fileno())
        for attempt in range(8):
            try:os.replace(temporary,p);break
            except PermissionError:
                # Windows may briefly deny replacement during another rename.
                if os.name!='nt' or attempt==7:raise
                time.sleep(.025*(attempt+1))
    finally:
        if temporary.exists():temporary.unlink()

def digest(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT).decode('utf-8')

def rel(p):return p.relative_to(ROOT).as_posix()
