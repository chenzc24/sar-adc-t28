"""One layout entry; native checks and managed simulation retain their own identities."""
import argparse,json,re,shlex,subprocess,sys
from Layout.project import ROOT,config,evidence,write_json

def physical(identity,through,module='cdac',rebuild=False,view='layout',rc_corner=None):
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{1,55}',identity):raise ValueError('Invalid physical ID')
    c=config();root=c['remote_root'];legacy=c['legacy_root']
    q=shlex.quote
    if rebuild and module not in ('comparator', 'bootstrap'):
        raise ValueError('Rebuild is supported only for generator-owned cores')
    if view != 'layout' and (module != 'cdac' or rebuild):
        raise ValueError('Alternate views are supported for existing CDAC layouts')
    if rc_corner is not None and (rc_corner not in ('cworst_T','cbest_T') or module not in ('sar-timing','sar-timing-filled') or through!='pex'):
        raise ValueError('Select cworst_T or cbest_T for a SAR PEX run')
    if module in ('sar-timing', 'sar-timing-filled'):
        sar = json.loads((ROOT/'Layout/design/manifest.json').read_text())['cells']['sar_timing']
        view = sar['view'] if module=='sar-timing' else sar['fill_view']
        arguments = ['python', '-u', 'qualify_sar_timing.py', identity, '--module', module,
                     '--view', view, '--through', through]
        if sar.get('generator') == 'Layout/design/sar_standard.py':
            arguments.append('--standard-delays')
        if rc_corner:
            arguments.extend(['--rc-corner',rc_corner])
    else:
        case = {'cdac':'full', 'comparator':'comparator', 'comparator-filled':'comparator-filled', 'bootstrap':'bootstrap'}[module]
        arguments = ['python','-u','run_physical.py',case,identity,'--through',through,'--pex-timeout','1800']
        if not rebuild:
            arguments.append('--existing-oa')
            if view != 'layout':
                arguments.extend(['--view',view])
        else:
            arguments.append('--rebuild-' + module)
    command=' '.join(q(x) for x in arguments)
    script='\n'.join(['set -eu','umask 077','cd '+q(root+'/runtime'),
        'if test -e '+q(root+'/evidence/'+identity)+' || test -e '+q(legacy+'/evidence/'+identity)+'; then echo "Evidence identity already exists; query status, do not resubmit." >&2; exit 2; fi',
        # noclobber provides a persistent submission guard before spawning.
        'set -C',': > '+q(root+'/state/'+identity+'.submitted'),'set +C',
        'nohup '+command+' > '+q(root+'/state/'+identity+'.driver')+' 2>&1 < /dev/null &','echo $!'])
    out=subprocess.check_output(['ssh',c['host'],'bash -s'],input=script.encode(),timeout=30).decode().strip()
    receipt={'host':c['host'],'identity':identity,'pid':int(out),'through':through,'existing_oa':not rebuild,'module':module,'view':view,
             'state_directory':root+'/state','resubmit':False}
    if rc_corner:receipt['interconnect_rc']=rc_corner
    write_json(ROOT/'work/layout/restructure'/('launch-'+identity+'.json'),receipt)
    return receipt

def status(identity):
    c=config();path=evidence(identity)
    raw=subprocess.check_output(['ssh',c['host'],'cat '+shlex.quote(path+'/manifest.json')],timeout=30)
    m=json.loads(raw)
    return {'identity':identity,'host':c['host'],'evidence':path,'error':m.get('error'),
        'phases':{k:{x:v[x] for x in ['status','returncode','verdict','markers_by_rule','bytes','sha256'] if x in v} for k,v in m['checks'].items()}}

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
    for name in ['check','render','deploy']:sub.add_parser(name)
    a=sub.add_parser('generate');a.add_argument('--module',choices=['cdac','cdac-paired','comparator','bootstrap','sar-timing'],default='cdac')
    a.add_argument('--initial',action='store_true',help='sar-timing only: reproduce the original RC placement')
    a.add_argument('--array',action='store_true',help='sar-timing only: reproduce the archived RC bit rows and MOM array')
    a.add_argument('--quiet-stages',type=int,choices=(5,6,9),help='sar-timing only: generate the specified standard-cell QUIET candidate')
    a.add_argument('--quiet-final-ps',type=int,choices=(200,250),help='Final delay cell for a six-stage standard-cell QUIET candidate')
    a.add_argument('--planned-fill',action='store_true',help='cdac-paired only: add the planned array fill cell')
    a.add_argument('--center',choices=['inverted','stacked'],help='cdac-paired only: small-bit layout of the two center columns')
    a=sub.add_parser('physical');a.add_argument('identity');a.add_argument('--through',choices=['stream','drc','lvs','pex'],default='pex')
    a.add_argument('--module',choices=['cdac','comparator','comparator-filled','bootstrap','sar-timing','sar-timing-filled'],default='cdac')
    a.add_argument('--rebuild',action='store_true',help='Rebuild a generator-owned core after a checkpoint')
    a.add_argument('--view',choices=['layout','layout_paired_balanced'],default='layout')
    a.add_argument('--rc-corner',choices=['cworst_T','cbest_T'],help='Foundry capacitance corner for a SAR PEX run')
    a=sub.add_parser('status');a.add_argument('identity')
    a=sub.add_parser('query-source', help='Locate archived layout evidence for historical runs')
    a.add_argument('selector')
    a.add_argument('--collect', action='store_true', help='Collect missing files from existing physical evidence')
    a=sub.add_parser('prepare-tt');a.add_argument('physical_identity');a.add_argument('run_id')
    a.add_argument('--prefill',action='store_true',help='Use the extracted CDAC before density fill')
    a.add_argument('--planned-fill',action='store_true',help='Use the extracted CDAC with its planned array fill')
    args=p.parse_args()
    if args.action=='physical':print(json.dumps(physical(args.identity,args.through,args.module,args.rebuild,args.view,args.rc_corner),indent=2))
    elif args.action=='status':print(json.dumps(status(args.identity),indent=2))
    elif args.action=='query-source':
        from Layout.query_source import resolve
        result, exit_code = resolve(args.selector, collect=args.collect)
        print(json.dumps(result, indent=2))
        raise SystemExit(exit_code)
    elif args.action in ['check','render']:
        from Layout.planning import check,render
        result=render() if args.action=='render' else check()
        print(json.dumps(result,indent=2))
        if result.get('valid') is False:raise SystemExit(1)
    else:
        generator = 'Layout.design.' + getattr(args,'module','cdac').replace('-','_')
        options=[]
        if args.action=='generate':
            if args.initial and args.module!='sar-timing':
                raise SystemExit('--initial applies to --module sar-timing')
            if args.module == 'sar-timing' and not (args.initial or args.array):
                active = json.loads((ROOT/'Layout/design/manifest.json').read_text())['cells']['sar_timing']
                generator = active['generator'].removesuffix('.py').replace('/', '.')
            if args.array:
                if args.module!='sar-timing' or args.initial:
                    raise SystemExit('--array requires --module sar-timing and a new placement')
                generator = 'Layout.design.sar_array'
            if args.quiet_stages is not None:
                if args.module != 'sar-timing' or args.initial or args.array:
                    raise SystemExit('--quiet-stages requires the standard-cell SAR placement')
                generator = 'Layout.design.sar_standard'
            if args.quiet_final_ps is not None and args.quiet_stages!=6:
                raise SystemExit('--quiet-final-ps requires --quiet-stages 6')
            if (args.planned_fill or args.center) and args.module!='cdac-paired':
                raise SystemExit('--planned-fill and --center apply to --module cdac-paired')
            options=(['--planned-fill'] if args.planned_fill else [])+(['--center',args.center] if args.center else [])
            if args.initial:
                options.append('--initial')
            if args.quiet_stages is not None:
                options.extend(['--quiet-stages',str(args.quiet_stages)])
            if args.quiet_final_ps is not None:
                options.extend(['--quiet-final-ps',str(args.quiet_final_ps)])
        modules={'generate':(generator,options),'deploy':('Layout.tools.deploy',['--apply']),
                 'prepare-tt':('Layout.tools.simulation.prepare_integrated_sim',
                               [getattr(args,'physical_identity',''),getattr(args,'run_id','')]+(['--prefill'] if getattr(args,'prefill',False) else [])
                               +(['--planned-fill'] if args.action=='prepare-tt' and args.planned_fill else []))}
        module,rest=modules[args.action]
        subprocess.run([sys.executable,'-m',module]+rest,cwd=ROOT,check=True)

if __name__=='__main__':main()
