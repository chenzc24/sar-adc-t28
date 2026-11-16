"""Owned remote workspace contract, compatible with the licensed Python 2 runtime."""
import json,os,re,socket
from os.path import join,realpath,dirname,isdir,exists

def paths():
    runtime=dirname(realpath(__file__))
    config=join(runtime,'workspace.json')
    with open(config) as f:c=json.load(f)
    root=realpath(c['remote_root'])
    expected=join(root,'runtime')
    if runtime!=expected or realpath(os.getcwd())!=expected:
        raise ValueError('Run from the configured owned runtime')
    if socket.gethostname().split('.')[0]!=c['host']:
        raise ValueError('Wrong physical execution host')
    for p in [root,runtime,join(root,'state'),join(root,'evidence'),c['legacy_root'],c['library_path']]:
        if not isdir(p) or os.stat(p).st_uid!=os.getuid():raise ValueError('Unowned/missing workspace: '+p)
    if os.stat(config).st_uid!=os.getuid():raise ValueError('Unowned configuration')
    c.update(runtime=runtime,state=join(root,'state'),evidence=join(root,'evidence'))
    # Keep the old inode as the shared lock; legacy tools cannot bypass it.
    c['lock']=join(c['legacy_root'],'layout.lock')
    if exists(c['lock']) and os.stat(c['lock']).st_uid!=os.getuid():raise ValueError('Unowned shared lock')
    return c

def state(name):
    if not re.match(r'\A[a-zA-Z0-9_.-]+\Z',name):raise ValueError('Unsafe state name')
    return join(paths()['state'],name)

def evidence(identity,create=False):
    if not re.match(r'\A[a-z0-9][a-z0-9-]{1,55}\Z',identity):raise ValueError('Unsafe evidence ID')
    c=paths();target=join(c['evidence'],identity)
    found=[p for p in [target,join(c['legacy_root'],'evidence',identity)] if exists(p)]
    if create:
        if found:raise ValueError('Evidence already exists; no resubmission: '+identity)
        os.mkdir(target);return target
    if len(found)!=1:raise ValueError('Evidence missing or ambiguous: '+identity)
    return found[0]
