"""Compare the full CDAC PEX against frozen B with existing module measurements."""
from __future__ import print_function
import argparse,glob,json,os
from native_stream import samples
from analyze_blocks import analyze


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--run-dir',required=True)
    p.add_argument('--output-dir',required=True)
    p.add_argument('--source-run-dir')
    args=p.parse_args()
    base=args.source_run_dir or args.run_dir
    files=glob.glob(base+'/raw/*.tran')
    if len(files)!=1:raise ValueError('Missing unique native transient')
    context=json.load(open(base+'/inputs/context.json'))
    last=None
    for t,v in samples(files[0]):last=t
    if last is None or abs(last-260e-9)>1e-15:raise ValueError('Incomplete transient')
    out={'analysis_complete':True,'physical_evidence':context['physical_evidence'],
         'gds_sha256':context['gds_sha256'],'scope':context['scope'],'stop_s':last}
    for prefix in ['pre','post']:
        def trace():
            for t,v in samples(files[0]):
                yield t,{key:v[prefix+'_'+key] for key in context['required_signals']}
        result=analyze(context,trace,{})
        out[prefix]={'metrics':result['metrics']['cdac'],
                     'failures':result['failures'],'diagnostics':result['diagnostics'],
                     'max_saved_step_s':result['max_saved_step_s']}
    pre,post=[out[n]['metrics'] for n in ['pre','post']]
    out['delta']={
        'weight_error_lsb':[(b-a)/(.9/128) for a,b in zip(pre['effective_weights_v'],post['effective_weights_v'])],
        'weight_ratio_post_pre':[b/a for a,b in zip(pre['effective_weights_v'],post['effective_weights_v'])],
        'settle_change_s':[b-a if a is not None and b is not None else None for a,b in zip(pre['settle_to_quarter_lsb_s'],post['settle_to_quarter_lsb_s'])]}
    out['physical_signoff']=False
    with open(args.output_dir+'/result.json','w') as f:json.dump(out,f,indent=2);f.write('\n')


if __name__=='__main__':main()
