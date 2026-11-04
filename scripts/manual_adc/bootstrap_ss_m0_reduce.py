from __future__ import print_function
import argparse,json,os
from reduce import frames
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-dir',required=True);ap.add_argument('--output-dir',required=True);a=ap.parse_args()
    cfg=json.load(open(a.run_dir+'/inputs/measure.json'));state=json.load(open(a.run_dir+'/simulation.state.json'))
    if state.get('exit_code')!=0 or not state.get('native',{}).get('zero_error_footer'):raise ValueError('native incomplete')
    src=[a.run_dir+'/raw/'+s for s in os.listdir(a.run_dir+'/raw') if s.endswith('.tran.tran')][0]
    first=None;last=None
    for t,v in frames(src):
        if first is None:first=v.copy()
        last=v
    if abs(t-2e-9)>1e-15:raise ValueError('stop mismatch')
    for c in cfg['cases']:
        i=-last[c['current']]
        if i<=0:raise ValueError('current polarity')
        c.update(Id_A=i,Rsmall_ohm=.001/i,transient_current_change_A=last[c['current']]-first[c['current']])
    cfg['native']=state['native'];json.dump(cfg,open(a.output_dir+'/result.json','w'),indent=2)
if __name__=='__main__':main()
