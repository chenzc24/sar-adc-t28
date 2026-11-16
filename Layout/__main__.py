"""One layout entry; native checks and managed simulation retain their own identities."""
import argparse,json,re,shlex,subprocess,sys
from Layout.project import ROOT,config,evidence,write_json

def physical(identity,through):
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{1,55}',identity):raise ValueError('Invalid physical ID')
    c=config();root=c['remote_root'];legacy=c['legacy_root']
    q=shlex.quote
    command=' '.join(q(x) for x in ['python','-u','run_physical.py','full',identity,'--existing-oa','--through',through,'--pex-timeout','1800'])
    script='\n'.join(['set -eu','umask 077','cd '+q(root+'/runtime'),
        'if test -e '+q(root+'/evidence/'+identity)+' || test -e '+q(legacy+'/evidence/'+identity)+'; then echo "Evidence identity already exists; query status, do not resubmit." >&2; exit 2; fi',
        # noclobber provides a persistent submission guard before spawning.
        'set -C',': > '+q(root+'/state/'+identity+'.submitted'),'set +C',
        'nohup '+command+' > '+q(root+'/state/'+identity+'.driver')+' 2>&1 < /dev/null &','echo $!'])
    out=subprocess.check_output(['ssh',c['host'],'bash -s'],input=script.encode(),timeout=30).decode().strip()
    receipt={'host':c['host'],'identity':identity,'pid':int(out),'through':through,'existing_oa':True,
             'state_directory':root+'/state','resubmit':False}
    write_json(ROOT/'work/layout/restructure'/('launch-'+identity+'.json'),receipt)
    return receipt

def status(identity):
    c=config();path=evidence(identity)
    raw=subprocess.check_output(['ssh',c['host'],'cat '+shlex.quote(path+'/manifest.json')],timeout=30)
    m=json.loads(raw)
    return {'identity':identity,'host':c['host'],'evidence':path,'error':m.get('error'),
        'phases':{k:{x:v[x] for x in ['status','returncode','verdict','markers_by_rule'] if x in v} for k,v in m['checks'].items()}}

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
    for name in ['check','render','generate','deploy']:sub.add_parser(name)
    a=sub.add_parser('physical');a.add_argument('identity');a.add_argument('--through',choices=['stream','drc','lvs','pex'],default='pex')
    a=sub.add_parser('status');a.add_argument('identity')
    a=sub.add_parser('prepare-tt');a.add_argument('physical_identity');a.add_argument('run_id')
    args=p.parse_args()
    if args.action=='physical':print(json.dumps(physical(args.identity,args.through),indent=2))
    elif args.action=='status':print(json.dumps(status(args.identity),indent=2))
    elif args.action in ['check','render']:
        from Layout.planning import check,render
        result=render() if args.action=='render' else check()
        print(json.dumps(result,indent=2))
        if result.get('valid') is False:raise SystemExit(1)
    else:
        modules={'generate':('Layout.design.cdac',[]),'deploy':('Layout.tools.deploy',['--apply']),
                 'prepare-tt':('Layout.tools.simulation.prepare_integrated_sim',
                               [getattr(args,'physical_identity',''),getattr(args,'run_id','')])}
        module,rest=modules[args.action]
        subprocess.run([sys.executable,'-m',module]+rest,cwd=ROOT,check=True)

if __name__=='__main__':main()
