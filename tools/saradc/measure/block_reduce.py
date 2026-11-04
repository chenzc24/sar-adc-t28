"""Bounded native module metrics; Python2.7/3, no whole-waveform arrays."""
from __future__ import print_function
import argparse,hashlib,json,math,os,re
from native_stream import samples

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(65536),b''):h.update(b)
    return h.hexdigest()

def random_evidence(root):
    p=root+'/raw/mismatch.params';v=root+'/raw/mismatch.values'
    if not os.path.exists(p):return {'files':[],'selected':{}}
    files=[{'path':os.path.relpath(q,root),'bytes':os.path.getsize(q),'sha256':sha(q)} for q in [p,v]]
    selected={};n=0
    with open(p) as names,open(v) as vals:
        cols=next(names).split();assert next(vals).strip()=='#1'
        ns=(x.strip() for x in names if x.strip());vs=(x.strip() for x in vals if x.strip())
        for name,line in zip(ns,vs):
            row=[float(x) for x in line.split()];assert len(row)==len(cols)
            assert all(not math.isnan(x) and not math.isinf(x) for x in row);n+=1
            if 'CMOM' in name.upper():selected[name]={'par_mom':row[cols.index('par_mom')]}
            elif 'MNIN' in name.upper():selected[name]={k:row[cols.index(k)] for k in ['plo_tox','parl1','parl2','parl3']}
        assert not list(ns) and not list(vs),'Mismatch scalar labels/data count differs'
    assert selected,'No target mismatch parameters saved'
    return {'files':files,'values_sha256':sha(v),'instance_rows':n,'selected':selected}

def cap_values(path):
    section=None;freq=None;vals={};out=[];ended=False
    def emit():
        if freq is not None:out.append((freq,dict(vals)))
    for raw in open(path):
        s=raw.strip()
        if s in ['HEADER','TYPE','SWEEP','TRACE','VALUE','END']:
            section=s
            if s=='END':emit();ended=True;break
            continue
        if section!='VALUE' or not s.startswith('"'):continue
        _,name,tail=s.split('"',2);tail=tail.strip()
        if name=='freq':emit();freq=float(tail);vals={}
        else:
            z=tail.strip('()').split()
            if len(z)==2:vals[name.lower()]=complex(float(z[0]),float(z[1]))
    assert ended and len(out)>=2
    return out

def weight_metrics(caps):
    totals={side:sum(caps[side+str(i)] for i in range(9)) for side in 'PN'}
    weights=[.9*(caps['P'+str(i)]/totals['P']+caps['N'+str(i)]/totals['N']) for i in range(8)]
    lsb=1.8/256.;levels=[sum(weights[b] for b in range(8) if code&(1<<b)) for code in range(256)]
    widths=[levels[i+1]-levels[i] for i in range(255)];ep=(levels[-1]-levels[0])/255
    dnl=[x/lsb-1 for x in widths];inl=[(x-i*ep)/ep for i,x in enumerate(levels)]
    carry=[{'bit':b,'step_v':weights[b]-sum(weights[:b]),'error_lsb':(weights[b]-sum(weights[:b]))/lsb-1} for b in range(8)]
    return {'total_cap_f':totals,'differential_weights_v':weights,'weight_error_lsb':[(w-lsb*(1<<b))/lsb for b,w in enumerate(weights)],
        'dac_dnl_nominal_lsb':dnl,'dac_dnl_abs_max_lsb':max(map(abs,dnl)),
        'dac_inl_endpoint_lsb':inl,'dac_inl_endpoint_abs_max_lsb':max(map(abs,inl)),
        'dac_levels_monotonic':all(x>0 for x in widths),'major_carry':carry,
        'scope':'Linearized capacitor-weight binary DAC level metrics; not complete SAR ADC transition DNL/INL'}

def cdac(root):
    paths=[]
    for d,dirs,fs in os.walk(root+'/raw'):
        paths += [d+'/'+x for x in fs if x.endswith('.ac')]
    assert len(paths)==1,paths
    data=cap_values(paths[0]);freq,v=data[0];caps={}
    for side in 'PN':
        for i in range(9):
            z=v['vcmom'+side.lower()+str(i)+':p'];c=-z.imag/(2*math.pi*freq);assert c>0
            caps[side+str(i)]=c
    other=data[-1];drift=[]
    for k,c in caps.items():drift.append(abs(-other[1]['vcmom'+k.lower()+':p'].imag/(2*math.pi*other[0])/c-1))
    return {'capacitance_f':caps,'weights':weight_metrics(caps),'ac_frequency_relative_spread_max':max(drift),
        'native_data_valid':max(drift)<1e-4,'native_ac_file':os.path.relpath(paths[0],root)}

def comparator(root,ctx,lines):
    records=[]
    for line in lines:
        m=re.search(r'CMPMC,([^\r\n]+)',line)
        if m:records.append([float(x) for x in m.group(1).split(',')])
    assert len(records)==ctx['cycles'] and all(len(x)==12 for x in records),(len(records),records[:1])
    paths=[]
    for d,dirs,fs in os.walk(root+'/raw'):paths += [d+'/'+x for x in fs if x.endswith('.tran.tran')]
    assert len(paths)==1,paths
    native={};points=0;cm_min=1e9;cm_max=-1e9
    for t,v in samples(paths[0]):
        points+=1;j=int(round((t-ctx['report_s'])/ctx['period_s']))
        if 0<=j<ctx['cycles'] and abs(t-(ctx['report_s']+j*ctx['period_s']))<1e-15:
            diff=v['pr']-v['nr'];native[j]={'polarity':1 if diff>.45 else -1 if diff<-.45 else 0,'input_diff_v':v['vinp']-v['vinn']}
        cm=(v['vinp']+v['vinn'])/2;cm_min=min(cm_min,cm);cm_max=max(cm_max,cm)
    assert len(native)==ctx['cycles'],len(native)
    for i,r in enumerate(records):
        assert int(r[0])==i and native[i]['polarity']==int(r[2])
        assert abs(native[i]['input_diff_v']-r[1])<1e-7
    final=records[ctx['search_steps']+1];lo,hi=final[4:6];offset=(lo+hi)/2
    speed=[{'cycle':int(r[0]),'overdrive_about_estimated_offset_v':r[1]-offset,'polarity':int(r[2]),'resolved':bool(r[3]),
        'raw_decision_ns':r[6]*1e9 if r[6]>=0 else None,'receiver_decision_ns':r[7]*1e9 if r[7]>=0 else None,
        'reset_min_v':r[8],'within_0p75ns_diagnostic':r[7]>=0 and r[7]<=.75e-9} for r in records[ctx['search_steps']+2:]]
    return {'native_data_valid':True,'native_event_crosscheck':True,'records':records,'native_points':points,
        'input_common_mode_range_v':[cm_min,cm_max],'offset_lower_v':lo,'offset_upper_v':hi,'offset_midpoint_v':offset,
        'offset_width_v':hi-lo,'guard_pass':final[9]==0,'unresolved_search_probes':int(final[10]),
        'threshold_valid':final[9]==0 and hi-lo<=2*ctx['search_range_v']/(2**ctx['search_steps'])*1.001,
        'speed_probes':speed,'scope':'Loaded effective threshold at1.75ns diagnostic window; native B shorter timing is a separate delay comparison, no complete handshake/kickback qualification'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--output-dir',required=True);a=p.parse_args()
    ctx=json.load(open(a.run_dir+'/inputs/context.json'));lines=list(open(a.run_dir+'/spectre.out'))
    r=cdac(a.run_dir) if ctx['family']=='cdac' else comparator(a.run_dir,ctx,lines)
    e=random_evidence(a.run_dir)
    if ctx['seed'] is not None:assert e['files']
    r.update(analysis_complete=True,context=ctx,mismatch_evidence=e,
        warning_codes=sorted(set(x for l in lines for x in re.findall(r'WARNING \(([^)]+)\)',l))),
        native_statistical_counts=[x.strip() for x in lines if re.search(r'Defined process parameters|Defined mismatch parameters|Number of random variables',x)],
        electrical_verdict='deferred_not_qualified')
    with open(a.output_dir+'/result.json','w') as f:json.dump(r,f,indent=2);f.write('\n')
    print('BLOCK_MC_ANALYSIS',ctx['family'],ctx['seed'],r['native_data_valid'])
if __name__=='__main__':main()
