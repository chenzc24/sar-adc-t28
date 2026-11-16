"""Local layout paths share the existing site's configuration and managed engine."""
import json
from pathlib import Path
import re
import shlex
import subprocess
import yaml

ROOT=Path(__file__).resolve().parents[1]

def config():
    cfg=yaml.safe_load((ROOT/'site.local.yaml').read_text(encoding='utf-8-sig'))['layout']
    for key in ['remote_root','library_path', 'legacy_root']:
        if not re.fullmatch(r'/[A-Za-z0-9_./-]+',cfg[key]) or '..' in cfg[key].split('/'):
            raise ValueError('Unsafe layout path: '+key)
    return cfg

def evidence(identity):
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{1,55}',identity):raise ValueError('Invalid evidence identity')
    c=config()
    paths=[c['remote_root']+'/evidence/'+identity,c['legacy_root']+'/evidence/'+identity]
    script='\n'.join('if test -d '+shlex.quote(p)+'; then printf "%s\\n" '+shlex.quote(p)+'; fi' for p in paths)
    found=subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10',c['host'],'bash -s'],input=script.encode(),timeout=30).decode().splitlines()
    if len(found)!=1:raise ValueError('Evidence missing or ambiguous: '+identity)
    return found[0]

def write_json(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
