"""Bounded Python2/3 native module and mixed-view observations."""
from __future__ import print_function
import argparse,glob,json,os,re
from native_stream import samples


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--output-dir',required=True)
    args=p.parse_args();base=args.run_dir
    context=json.load(open(base+'/inputs/context.json'))
    names=context['profiles'];codes=context['expected_codes'];fault=context.get('fault_profile')
    issues=[];warnings=set();probes={};sar={};unit={};gate_overlap=0
    for line in open(base+'/spectre.out'):
        warnings.update(re.findall(r'WARNING \(([^)]+)\)',line))
        m=re.search(r'BPROBE,(\d+),(\d+),(\d+)',line)
        if m:
            key=(int(m.group(1)),int(m.group(2)))
            if key in probes:issues.append(['duplicate_probe',key])
            probes[key]=int(m.group(3))
        m=re.search(r'BSAR,([^\r\n]+)',line)
        if m:
            row=m.group(1).split(',');key=(int(row[0]),int(row[1]))
            sar[key]=[float(x) for x in row[2:]]
    expected={(i,j):(0 if i==fault else code) for i in range(len(names)) for j,code in enumerate(codes)}
    for key,value in sorted(expected.items()):
        if probes.get(key)!=value:issues.append(['pin_code',key,probes.get(key),value])
    for key in set(probes)-set(expected):issues.append(['extra_probe',key])
    # Count electrical CMP_CLK/PHI_U edges in the actual conversion window.
    rows={(i,j):dict(comparisons=0,updates=0,valid_responses=0,first_compare_s=None,last_update_s=None,max_decision_s=0.)
          for i in range(len(names)) if i!=fault for j in range(len(codes))}
    raw=glob.glob(base+'/raw/*.tran');previous={};begins={};responded={};checked_traces=False
    if len(raw)!=1:issues.append(['native_wave_file_count',len(raw)])
    else:
        for t,values in samples(raw[0]):
            if not checked_traces:
                required={instance+'.'+pin for i,instance in enumerate(context['instance_names']) if i!=fault
                          for pin in ['cmp_clk','phi_u','comp_n','comp_p']}
                if context.get('native_unit_tests'):
                    required.update('x1.'+p+str(k) for p in ['gnn','gnp','gpn','gpp'] for k in range(8))
                    required.update(['unit_hold','unit_outn','unit_outp'])
                missing=sorted(required-set(values))
                if missing:issues.append(['missing_saved_signals',missing])
                checked_traces=True
            for i,instance in enumerate(context['instance_names']):
                if i==fault:continue
                frame=int((t-context['frame_origin_s'])/context['period_s'])
                if t<context['frame_origin_s'] or not 0<=frame<len(codes):continue
                close=context['frame_origin_s']+frame*context['period_s']
                if t>=close+59.9e-9:continue
                row=rows[(i,frame)];clk=instance+'.cmp_clk';phi=instance+'.phi_u'
                if values.get(clk,0)>.45 and previous.get(clk,0)<=.45:
                    row['comparisons']+=1;begins[i]=t;responded[i]=False
                    if row['first_compare_s'] is None:row['first_compare_s']=t
                if values.get(phi,0)>.45 and previous.get(phi,0)<=.45:
                    row['updates']+=1;row['last_update_s']=t
                if values.get(clk,0)>.45 and min(values.get(instance+'.comp_n',.9),values.get(instance+'.comp_p',.9))<.45 and not responded.get(i,True):
                    row['valid_responses']+=1;responded[i]=True
                    row['max_decision_s']=max(row['max_decision_s'],t-begins[i])
            if context.get('native_unit_tests'):
                for tag,at in [('hold_initial',110e-9),('hold_after_input_step',150e-9),('track_new_input',190e-9),('comparator_positive',10e-9),('comparator_reset',20e-9),('comparator_negative',170e-9)]:
                    if tag not in unit and t>=at:
                        unit[tag]=dict(time_s=t,held_v=values.get('unit_hold'),outn_v=values.get('unit_outn'),outp_v=values.get('unit_outp'))
                for k in range(8):
                    for gn,gp in [('gnn','gnp'),('gpn','gpp')]:
                        if values.get('x1.'+gn+str(k),0)>.45 and values.get('x1.'+gp+str(k),.9)<.45:gate_overlap+=1
            previous=values
    for key,row in sorted(rows.items()):
        if row['comparisons']!=8 or row['updates']!=8 or row['valid_responses']!=8:
            issues.append(['electrical_event_counts',key,row])
    if context.get('native_unit_tests'):
        for tag,target in [('hold_initial',.2),('hold_after_input_step',.2),('track_new_input',.8)]:
            if tag not in unit or abs(unit[tag]['held_v']-target)>1e-4:issues.append(['sampler',tag,unit.get(tag),target])
        for tag,levels in [('comparator_positive',(0,.9)),('comparator_reset',(.9,.9)),('comparator_negative',(.9,0))]:
            r=unit.get(tag,{})
            if any(r.get(key) is None or abs(r[key]-target)>.02 for key,target in zip(['outn_v','outp_v'],levels)):
                issues.append(['comparator',tag,r,levels])
        if gate_overlap:issues.append(['reference_gate_overlap_samples',gate_overlap])
        for i,name in enumerate(names):
            if name in ['current','control_xtor']:continue
            for j in range(len(codes)):
                got=sar.get((i,j))
                if got is None:issues.append(['missing_sar_trace',i,j]);continue
                want=[1,0,0,0] if i==fault else [8,8,8,16]
                if got[1:5]!=want:issues.append(['sar_counts',i,j,got[1:5],want])
                if bool(got[-2])!=(i==fault):issues.append(['sar_completion',i,j,got[-2:]])
    result=dict(module_validation=True,analysis_complete=True,pass_validation=not issues,profiles=names,pin_probes=len(probes),
                failures=issues[:40],failure_count=len(issues),warning_codes=sorted(warnings),
                gate_overlap_samples=gate_overlap,unit_measurements=unit,
                frames=[dict(profile=names[i],frame=j,**row) for (i,j),row in sorted(rows.items())],context=context,
                scope='Loaded TT module behavior, public-pin mixed function and event counts. No PVT, mismatch, analog-accuracy, power or terminal-reliability qualification.')
    with open(args.output_dir+'/result.json','w') as out:json.dump(result,out,indent=2);out.write('\n')
    assert not issues,'Modular native validation failed; see derived/result.json'
    print('MODULAR_VALIDATION_OK',len(probes))


if __name__=='__main__':main()
