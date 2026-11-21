"""One layout entry; native checks and managed simulation retain their own identities."""
import argparse,json,re,shlex,subprocess,sys
from Layout.project import ROOT,config,evidence,write_json

def physical(identity,through,module='cdac',rebuild=False,view=None,staging=None,rc_corner=None):
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{1,55}',identity):raise ValueError('Invalid physical ID')
    c=config();root=c['remote_root'];legacy=c['legacy_root']
    q=shlex.quote
    if module == 'sar-se':
        # The single-edge SAR macro: a revision view of sar8_se_core in SAR_ADC_T28_LAYOUT, built from DEF records.
        if not staging or not re.fullmatch(r'sar-se-[a-z0-9-]+',staging):raise ValueError('Select the sar-se staging directory')
        if not view or not re.fullmatch(r'layout_r\d+',view):raise ValueError('Select the sar8_se_core revision view, e.g. layout_r2')
        arguments = ['python','-u','sar_se_physical.py',identity,'--staging',staging,'--view',view,'--through',through]
        if rebuild:
            arguments.append('--build')
        if rc_corner:
            arguments.extend(['--rc-corner',rc_corner])
    else:
        view = view or 'layout'
        candidate_view = module == 'bootstrap' and re.fullmatch(r'layout_mmain\d{1,2}', view)
        if view not in ('layout','layout_paired_balanced') and not candidate_view:raise ValueError('Unknown layout view '+view)
        if staging or rc_corner:raise ValueError('--staging and --rc-corner apply to --module sar-se')
        if rebuild and module not in ('comparator', 'bootstrap'):
            raise ValueError('Rebuild is supported only for generator-owned cores')
        if view != 'layout' and not candidate_view and (module != 'cdac' or rebuild):
            raise ValueError('Alternate views are supported for existing CDAC layouts and Bootstrap candidates')
        case = {'cdac':'full', 'comparator':'comparator', 'comparator-filled':'comparator-filled', 'bootstrap':'bootstrap'}[module]
        arguments = ['python','-u','run_physical.py',case,identity,'--through',through,'--pex-timeout','1800']
        if not rebuild:
            arguments.append('--existing-oa')
            if view != 'layout':
                arguments.extend(['--view',view])
        else:
            arguments.append('--rebuild-' + module)
            if view != 'layout':
                arguments.extend(['--view',view])
    command=' '.join(q(x) for x in arguments)
    script='\n'.join(['set -eu','umask 077','cd '+q(root+'/runtime'),
        'if test -e '+q(root+'/evidence/'+identity)+' || test -e '+q(legacy+'/evidence/'+identity)+'; then echo "Evidence identity already exists; query status, do not resubmit." >&2; exit 2; fi',
        # noclobber provides a persistent submission guard before spawning.
        'set -C',': > '+q(root+'/state/'+identity+'.submitted'),'set +C',
        'nohup '+command+' > '+q(root+'/state/'+identity+'.driver')+' 2>&1 < /dev/null &','echo $!'])
    out=subprocess.check_output(['ssh',c['host'],'bash -s'],input=script.encode(),timeout=30).decode().strip()
    receipt={'host':c['host'],'identity':identity,'pid':int(out),'through':through,'existing_oa':not rebuild,'module':module,'view':view,
             'state_directory':root+'/state','resubmit':False}
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
    a=sub.add_parser('generate');a.add_argument('--module',choices=['cdac','cdac-paired','comparator','bootstrap'],default='cdac')
    a.add_argument('--planned-fill',action='store_true',help='cdac-paired only: add the planned array fill cell')
    a.add_argument('--center',choices=['inverted','stacked'],help='cdac-paired only: small-bit layout of the two center columns')
    a.add_argument('--candidate',help='bootstrap only: LVS source of an unselected sampler candidate')
    a=sub.add_parser('physical');a.add_argument('identity');a.add_argument('--through',choices=['stream','drc','lvs','pex'],default='pex')
    a.add_argument('--module',choices=['cdac','comparator','comparator-filled','bootstrap','sar-se'],default='cdac')
    a.add_argument('--rebuild',action='store_true',help='Rebuild a generator-owned core after a checkpoint; sar-se: create the view')
    a.add_argument('--view',help='layout or layout_paired_balanced for the CDAC; layout_rN for sar-se')
    a.add_argument('--staging',help='sar-se only: state directory with the DEF build records')
    a.add_argument('--rc-corner',choices=['cworst_T','cbest_T'],help='sar-se only: foundry interconnect corner for PEX')
    a=sub.add_parser('status');a.add_argument('identity')
    a=sub.add_parser('query-source', help='Locate archived layout evidence for historical runs')
    a.add_argument('selector')
    a.add_argument('--collect', action='store_true', help='Collect missing files from existing physical evidence')
    a=sub.add_parser('prepare-tt');a.add_argument('physical_identity');a.add_argument('run_id')
    a.add_argument('--prefill',action='store_true',help='Use the extracted CDAC before density fill')
    a.add_argument('--planned-fill',action='store_true',help='Use the extracted CDAC with its planned array fill')
    args=p.parse_args()
    if args.action=='physical':print(json.dumps(physical(args.identity,args.through,args.module,args.rebuild,args.view,args.staging,args.rc_corner),indent=2))
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
            if (args.planned_fill or args.center) and args.module!='cdac-paired':
                raise SystemExit('--planned-fill and --center apply to --module cdac-paired')
            options=(['--planned-fill'] if args.planned_fill else [])+(['--center',args.center] if args.center else [])
            if args.candidate:
                if args.module!='bootstrap':raise SystemExit('--candidate applies to --module bootstrap')
                options+=['--candidate',args.candidate]
        modules={'generate':(generator,options),'deploy':('Layout.tools.deploy',['--apply']),
                 'prepare-tt':('Layout.tools.simulation.prepare_integrated_sim',
                               [getattr(args,'physical_identity',''),getattr(args,'run_id','')]+(['--prefill'] if getattr(args,'prefill',False) else [])
                               +(['--planned-fill'] if args.action=='prepare-tt' and args.planned_fill else []))}
        module,rest=modules[args.action]
        subprocess.run([sys.executable,'-m',module]+rest,cwd=ROOT,check=True)

if __name__=='__main__':main()
