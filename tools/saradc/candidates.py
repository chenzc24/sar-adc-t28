"""Named physical implementations with source-bound, independently qualified results."""
import hashlib
import json
from pathlib import Path
import re
ROOT = Path(__file__).resolve().parents[2]
SUBCKT = re.compile(r'(?ms)^subckt (\w+)\b.*?^ends \1\b[^\n]*')
ID = re.compile(r'^[a-z0-9][a-z0-9_-]*$')


def definitions(text):
    return {m.group(1): m.group() for m in SUBCKT.finditer(text.replace('\\\n', ' '))}


def read(root=None):
    return json.loads(((root or ROOT)/'specs/candidates.json').read_text(encoding='utf-8'))


def assignments(items):
    result = {}
    for item in items or []:
        key, sep, value = item.partition('=')
        if not sep or not ID.fullmatch(key) or not ID.fullmatch(value):
            raise ValueError('Expected module=candidate: '+item)
        if key in result: raise ValueError('Duplicate module assignment: '+key)
        result[key] = value
    return result


def validate(module, record, row, root):
    path = (root/record['file']).resolve()
    if not path.is_relative_to((root/'design/xtor').resolve()) or not path.is_file():
        raise ValueError('Candidate must be an existing project design/xtor file')
    text = path.read_text(encoding='utf-8')
    if re.search(r'(?mi)^\s*(?:include|ahdl_include|\.include)\b', text):
        raise ValueError('Candidate definitions must not include external inputs')
    defs = definitions(text)
    remainder=SUBCKT.sub('',text.replace('\\\n',' '))
    if any(line.strip() and not line.lstrip().startswith('//') for line in remainder.splitlines()):
        raise ValueError('Candidate contains subcircuit definitions only; no global/model statements')
    for master, ports in row['interfaces'].items():
        if master not in defs or defs[master].splitlines()[0].split()[2:] != ports:
            raise ValueError('Candidate interface differs: '+module+'/'+master)
    return path, defs


def selected(overrides=None, root=None):
    root=root or ROOT;rows=read(root)['modules'];overrides=overrides or {}
    if set(overrides)-set(rows): raise ValueError('Unknown candidate module')
    result={}
    for module,row in rows.items():
        name=overrides.get(module,row['selected'])
        if name not in row['candidates']: raise ValueError('Unknown candidate: '+module+'='+name)
        path,defs=validate(module,row['candidates'][name],row,root)
        result[module]=dict(module=module,candidate=name,file=path.relative_to(root.resolve()).as_posix(),
                            target=row['target'],sha256=hashlib.sha256(path.read_bytes()).hexdigest(),definitions=defs)
    return result


def catalog(root=None):
    root=root or ROOT;result=[]
    for module,row in read(root)['modules'].items():
        for name,record in row['candidates'].items():
            path,_=validate(module,record,row,root)
            result.append(dict(module=module,candidate=name,file=record['file'],selected=name==row['selected'],
                               sha256=hashlib.sha256(path.read_bytes()).hexdigest(),status=record['status'],
                               qualification='Acceptance requires matching source hashes and measured scope'))
    return result


def add(module,name,filename,root=None):
    root=root or ROOT
    if not ID.fullmatch(name): raise ValueError('Invalid candidate ID')
    data=read(root)
    if module not in data['modules']: raise ValueError('Unknown candidate module')
    row=data['modules'][module]
    if name in row['candidates']: raise ValueError('Candidate already registered')
    path=(root/filename).resolve()
    record={'file':path.relative_to(root.resolve()).as_posix(),'status':'unqualified'}
    validate(module,record,row,root)
    row['candidates'][name]=record
    from .managed.project import save
    save(root/'specs/candidates.json',data)
    return dict(registered=module+'='+name,selected=row['selected'],status='unqualified')
