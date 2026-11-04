"""Native bounded held-input/sample-identity measurements; Python2.7/3."""
from __future__ import print_function
import argparse,collections,hashlib,json,math,os,re
from native_stream import samples

def mismatch(root,expected):
    if not expected['rows']:return {'required':False,'identical':True,'rows_checked':0}
    path=root+'/raw/mismatch.params';value=root+'/raw/mismatch.values'
    with open(path) as f:names=[x.strip() for x in f if x.strip()]
    cols=names.pop(0).split()
    with open(value) as f:vals=[x.strip() for x in f if x.strip()]
    assert vals.pop(0)=='#1' and len(names)==len(vals)
    rows={k:[float(x) for x in v.split()] for k,v in zip(names,vals)}
    missing=[];changed=[]
    for name,values in expected['rows'].items():
        if name not in rows:missing.append(name);continue
        current=[rows[name][cols.index(c)] for c in expected['columns']]
        if current!=values:changed.append(name)
    return {'required':True,'identical':not missing and not changed,'rows_checked':len(expected['rows']),
      'missing':missing,'changed':changed,'native_rows':len(rows),'expected_source_run':expected['source_run_id'],
      'source_values_sha256':expected['values_sha256'],'current_values_sha256':hashlib.sha256(open(value,'rb').read()).hexdigest()}

def interp(a,b,t):
    u=(t-a[0])/(b[0]-a[0]);return {k:a[1][k]+u*(b[1][k]-a[1][k]) for k in a[1]}

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--output-dir',required=True);a=p.parse_args()
    ctx=json.load(open(a.run_dir+'/inputs/context.json'));expected=json.load(open(a.run_dir+'/inputs/expected_mismatch.json'))
    lines=list(open(a.run_dir+'/spectre.out'));records=[]
    for l in lines:
        m=re.search(r'PHYSMC,([^\r\n]+)',l)
        if m:records.append([float(x) for x in m.group(1).split(',')])
    assert len(records)==ctx['cycles'] and all(len(x)==15 and int(x[0])==i for i,x in enumerate(records))
    mapping=mismatch(a.run_dir,expected);paths=[]
    for d,dirs,fs in os.walk(a.run_dir+'/raw'):paths += [d+'/'+n for n in fs if n.endswith('.tran.tran')]
    assert len(paths)==1
    prev=None;history=collections.deque();points=0;active=None;pulses=[];native={};pre={};traces=[]
    def vector(v):
        return {'vinp':v['vinp'],'vinn':v['vinn'],'vdiff':v['vinp']-v['vinn'],'cm':(v['vinp']+v['vinn'])/2,
          'pr':v['pr'],'nr':v['nr'],'op':v['op'],'on':v['on'],'clk':v['clk'],
          'source_diff':v['sip']-v['sin'],'main_vgs_p':v['xhold.xbootp.g']-v['xhold.ip'],'main_vgs_n':v['xhold.xbootn.g']-v['xhold.in']}
    for t,vals in samples(paths[0]):
        points+=1;v=vector(vals)
        if prev:
            pt,pv=prev
            frame=int(round((t-ctx['report_s'])/ctx['period_s']))
            if 0<=frame<ctx['cycles'] and pt<=ctx['report_s']+frame*ctx['period_s']<=t:
                x=interp(prev,(t,v),ctx['report_s']+frame*ctx['period_s']);native[frame]=x
            framep=int(round((t-ctx['pre_s'])/ctx['period_s']))
            if 0<=framep<ctx['cycles'] and pt<=ctx['pre_s']+framep*ctx['period_s']<=t:
                pre[framep]=interp(prev,(t,v),ctx['pre_s']+framep*ctx['period_s'])
            if pv['clk']<.45<=v['clk']:
                f=(.45-pv['clk'])/(v['clk']-pv['clk']);tr=pt+f*(t-pt);target=tr-100e-12;baseline=pv
                for h1,h2 in zip(list(history)[:-1],list(history)[1:]):
                    if h1[0]<=target<=h2[0]:baseline=interp(h1,h2,target);break
                active={'index':len(pulses),'rise_s':tr,'pre_vdiff_v':baseline['vdiff'],'pre_cm_v':baseline['cm'],
                  'peak_diff_change_v':0,'peak_cm_change_v':0,'raw_delay_s':None,'receiver_delay_s':None,
                  'main_vgs_p_pre_v':baseline['main_vgs_p'],'main_vgs_n_pre_v':baseline['main_vgs_n']}
            if active:
                active['peak_diff_change_v']=max(active['peak_diff_change_v'],abs(v['vdiff']-active['pre_vdiff_v']))
                active['peak_cm_change_v']=max(active['peak_cm_change_v'],abs(v['cm']-active['pre_cm_v']))
                for key,ns in [('raw_delay_s',('op','on')),('receiver_delay_s',('pr','nr'))]:
                    before=abs(pv[ns[0]]-pv[ns[1]]);now=abs(v[ns[0]]-v[ns[1]])
                    if active[key] is None and before<.45<=now:
                        crossing=pt+(.45-before)/(now-before)*(t-pt);active[key]=crossing-active['rise_s']
                if pv['clk']>.45>=v['clk']:
                    f=(.45-pv['clk'])/(v['clk']-pv['clk']);active['fall_s']=pt+f*(t-pt)
                    active['receiver_polarity_at_fall']=1 if v['pr']-v['nr']>.45 else -1 if v['pr']-v['nr']<-.45 else 0
                    pulses.append(active);active=None
        frame=int(math.floor((t-ctx['first_clock_rise_s'])/ctx['period_s']+.5))
        if frame in [0,11,14] and -200e-12<=t-(ctx['first_clock_rise_s']+frame*ctx['period_s'])<=1.1e-9:
            traces.append([t]+[v[k] for k in ['vinp','vinn','source_diff','clk','op','on','pr','nr','main_vgs_p','main_vgs_n']])
        history.append((t,v))
        while len(history)>2 and history[1][0]<t-300e-12:history.popleft()
        prev=(t,v)
    assert t>=ctx['stop_s']-1e-14 and len(native)==ctx['cycles'] and len(pre)==ctx['cycles'],(t,len(native),len(pre))
    assert len(pulses)==ctx['cycles']*8,len(pulses)
    max_native_error=0
    for i,row in enumerate(records):
        x=native[i];pol=1 if x['pr']-x['nr']>.45 else -1 if x['pr']-x['nr']<-.45 else 0
        assert pol==int(row[2]);assert abs(pre[i]['vdiff']-row[5])<1e-6
        max_native_error=max(max_native_error,abs(pre[i]['vdiff']-row[5]))
        assert abs(x['source_diff']-row[1])<1e-7
    end=records[ctx['search_steps']+1];first=pulses[::8]
    for i,row in enumerate(records):
        if row[10]>=0:assert abs(first[i]['receiver_delay_s']-row[10])<2e-12
    warning_codes=sorted(set(x for l in lines for x in re.findall(r'WARNING \(([^)]+)\)',l)))
    warnings=[{'line':i+1,'text':l.strip(),'context':lines[max(0,i-1)].strip()} for i,l in enumerate(lines) if 'WARNING (' in l or 'CMI-' in l]
    r={'analysis_complete':True,'native_data_valid':mapping['identical'],'context':ctx,'sample_mapping':mapping,'native_points':points,
      'native_event_crosscheck':True,'pre_native_vs_VA_error_v':max_native_error,'records':records,'pulses':pulses,'first_pulses':first,
      'source_threshold_interval_v':end[3:5],'source_offset_midpoint_v':sum(end[3:5])/2,
      'held_threshold_interval_v':end[7:9],'held_offset_midpoint_v':sum(end[7:9])/2,
      'threshold_valid':end[12]==0 and end[13]==0 and end[4]-end[3]<.000126,
      'held_pre_cm_v_range':[min(row[6] for row in records),max(row[6] for row in records)],
      'first_pulse_diff_kick_v_range':[min(x['peak_diff_change_v'] for x in first),max(x['peak_diff_change_v'] for x in first)],
      'warning_codes':warning_codes,'warning_entries':warnings,'electrical_verdict':'deferred_not_qualified',
      'trace_columns':['time_s','vinp','vinn','source_diff','clk','op','on','pr','nr','main_vgs_p','main_vgs_n'],'trace':traces}
    with open(a.output_dir+'/result.json','w') as f:json.dump(r,f,indent=2);f.write('\n')
    print('PHYSICAL_INPUT_ANALYSIS',ctx['run_id'],mapping['identical'],r['threshold_valid'],r['held_offset_midpoint_v'])
if __name__=='__main__':main()
