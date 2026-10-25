"""Frozen full-hierarchy real-load screens; no remote launch or OA mutation."""
import argparse
import json
import re
import yaml
from prepare import ROOT, BASE, digest, mapping
from io_screen import CORNERS

SEED=ROOT/'netlist/experiments/sar8_physical_repair/loaded_seed'

def archive_seed():
    """Small generated circuit snapshot, not PDK or raw waveform data."""
    SEED.mkdir(parents=True,exist_ok=True)
    old=(BASE/'dut.scs').read_text()
    test=(BASE/'test.scs').read_text().replace(old,'include "dut.scs"\n',1)
    test=re.sub(r'^save .*\n','',test,flags=re.M)
    content={'dut.scs':old,'test.scs':test,'r4_perf_monitor.va':(BASE/'r4_perf_monitor.va').read_text()}
    for name,value in content.items():
        target=SEED/name
        if target.exists():assert target.read_text()==value
        else:target.write_text(value)
    # Preserve the observer byte-for-byte, including its original line endings.
    (SEED/'r4_perf_monitor.va').write_bytes((BASE/'r4_perf_monitor.va').read_bytes())
    print(json.dumps({n:digest(SEED/n) for n in content},indent=2))


def parser_source():
    src=(ROOT/'scripts/sar8_ref_current_probe/stream_psf.cpp').read_text()
    src=src.replace('bool have=false', 'double exported=-1;unsigned long long exported_points=0;bool have=false')
    before='binary.write(reinterpret_cast<char*>(&t),8);for(int i:selectidx){double v=val(i);binary.write(reinterpret_cast<char*>(&v),8);}'
    assert before in src
    src=src.replace(before, 'if(t-exported>=20e-12 || section=="END") {'+before+'exported=t;++exported_points;}')
    src=src.replace('<<points<<",\\\"last_time_s', '<<exported_points<<",\\\"native_points\\\":"<<points<<",\\\"last_time_s')
    # Configuration is next to selected.txt; every native interval is integrated,
    # including an interpolated split at each 100 ns frame boundary.
    decl='''
 struct Product {string name,a,b;int ai,bi;double prev=0;double integral[2]={0,0};};
 vector<Product> products;string config=argv[2];config=config.substr(0,config.find_last_of("/\\\\")+1);
 ifstream powerfile(config+"products.txt");while(getline(powerfile,line)){istringstream s(line);Product p;s>>p.name>>p.a>>p.b;if(!p.name.empty())products.push_back(p);}
 vector<string> eventnames;vector<int> eventidx;vector<double> eventprev;
 ifstream eventfile(config+"events.txt");while(getline(eventfile,line)){if(!line.empty()&&line.back()=='\\r')line.pop_back();if(!line.empty())eventnames.push_back(line);}
 ofstream eventout(prefix+".events.tsv");eventout<<setprecision(17);int supplyidx=-1;
'''
    src=src.replace(' auto snapshot=[&](){', decl+'\n auto snapshot=[&](){')
    src=src.replace('  oldtime=t;++points;', '''
  for(auto &p:products){double current=val(p.ai)*val(p.bi);
   if(oldtime>=0){for(int f=0;f<2;++f){double a=max(oldtime,f*100e-9),b=min(t,(f+1)*100e-9);
    if(b>a){double ya=p.prev+(current-p.prev)*(a-oldtime)/(t-oldtime),yb=p.prev+(current-p.prev)*(b-oldtime)/(t-oldtime);p.integral[f]+=.5*(ya+yb)*(b-a);}}}
   p.prev=current;
  }
  for(size_t i=0;i<eventidx.size();++i){double current=val(eventidx[i])-.5*val(supplyidx);
   if(oldtime>=0 && ((eventprev[i]<0 && current>=0)||(eventprev[i]>0 && current<=0)))
    eventout<<eventnames[i]<<'\\t'<<(current>eventprev[i]?1:0)<<'\\t'<<(oldtime-eventprev[i]*(t-oldtime)/(current-eventprev[i]))<<'\\n';
   eventprev[i]=current;
  }
  oldtime=t;++points;''')
    src=src.replace('    ofstream cols(prefix+".columns");', '''
    for(auto &p:products){p.ai=index(p.a);p.bi=index(p.b);}
    supplyidx=index("vdd!");for(auto &n:eventnames)eventidx.push_back(index(n));eventprev.resize(eventidx.size());
    ofstream cols(prefix+".columns");''')
    src=src.replace(' ofstream stress(prefix+', ''' ofstream energy(prefix+".products.tsv");energy<<setprecision(17);
 for(auto&p:products)for(int f=0;f<2;++f)energy<<p.name<<'\\t'<<f<<'\\t'<<p.integral[f]<<'\\n';
 ofstream stress(prefix+''')
    assert 'native_points' in src and 'products.tsv' in src
    return src


def build(mode,corner,tail=4,reset=2,verify_existing=False,screen=False,platch=2,receiver=0,reverse=False,stop_ns=200):
    assert stop_ns in [200,210]
    process,sup,temp=CORNERS[corner]
    suffix='' if (tail,reset)==(4,2) else '-t%d-r%d'%(tail,reset)
    if platch!=2:suffix+='-p%d'%platch
    if receiver:suffix+='-rx%d'%receiver
    if reverse:suffix+='-rev'
    if stop_ns!=200:suffix+='-end%d'%stop_ns
    if screen:suffix+='-screen'
    run='sar8fix-loaded-'+mode+suffix+'-'+corner
    folder=ROOT/'output/sar8_physical_repair'/run
    assert verify_existing or not folder.exists(), 'Immutable candidate already exists'
    cdf=json.loads((ROOT/'verification/sar8_physical_repair/io_cdf_audit.json').read_text())
    cdf.update(json.loads((ROOT/'verification/sar8_physical_repair/native_cdf_audit.json').read_text()))
    seed=SEED if SEED.exists() else BASE
    old=(seed/'dut.scs').read_text();dut=old;changes=[]

    def replacement(m,which,bit=None):
        name,nodes,model,params=m.groups()
        if which=='receiver':newmodel=model[0]+'ch_18_mac';multi=receiver*(2 if model[0]=='p' else 1)
        elif which=='ref':newmodel=model[0]+'ch_18_mac';multi=2*2**bit
        elif name in ['MNINP','MNINN','MNLATP','MNLATN']:
            newmodel='nch_na18_mac';multi=8 if name.startswith('MNIN') else 4
        else:
            newmodel=model[0]+'ch_18_mac';multi=tail if name=='MNTAIL' else reset if name.startswith('MPRST') else platch
        pars=dict(cdf[newmodel]['parameters']);pars['multi']=multi
        for k in ['spmb','spmt']:
            if pars[k]=='1.11111P':pars[k]='1.11111e15'
        return '    '+name+' ('+nodes+') '+newmodel+' '+' '.join(k+'='+str(v) for k,v in pars.items())

    pattern=r'(?m)^\s*(M\w+)\s+\(([^)]*)\)\s+([np]ch_mac)([^\n]*)'
    cells=([('sar8j_r1_sw_b%d'%b,'ref',b) for b in range(8)] if mode in ['ref','both'] else [])
    if mode in ['comp','both']:cells.append(('sar_strongarm_t28','comp',None))
    for cell,which,bit in cells:
        block=re.search(r'(?ms)^subckt '+cell+r' .*?^ends '+cell,dut)[0]
        flat=block.replace('\\\n',' ')
        new,count=re.subn(pattern,lambda m:replacement(m,which,bit),flat)
        assert count==(2 if which=='ref' else 11),(cell,count)
        dut=dut.replace(block,new,1);changes.append(dict(cell=cell,changed_MOS=count))
    if receiver:
        assert mode in ['comp','both']
        inv=re.search(r'(?ms)^subckt sar8p_inv .*?^ends sar8p_inv',dut)[0]
        inv,n=re.subn(pattern,lambda m:replacement(m,'receiver'),inv.replace('\\\n',' '));assert n==2
        inv=inv.replace('sar8p_inv','sar8fix_recv_inv')
        buf=re.search(r'(?ms)^subckt sar8p_buf .*?^ends sar8p_buf',dut)[0]
        assert 'X000 (A VDD VSS N) sar8p_inv' in buf,buf
        buf=buf.replace('sar8p_buf','sar8fix_recv_buf').replace('X000 (A VDD VSS N) sar8p_inv','X000 (A VDD VSS N) sar8fix_recv_inv')
        timing=re.search(r'(?ms)^subckt sar8p_timing .*?^ends sar8p_timing',dut)[0]
        changed_timing,n=re.subn(r'(?m)(^\s*X00[23] \([^\n]*\)) sar8p_buf',r'\1 sar8fix_recv_buf',timing);assert n==2
        dut=dut.replace(timing,changed_timing,1)+'\n'+inv+'\n'+buf+'\n'
        changes.append(dict(cell='sar8p_timing COMP_P/N input inverter only',changed_MOS=4))
    original=mapping(old);devices=mapping(dut)
    assert set(original)==set(devices)
    changed=[k for k in original if original[k]!=devices[k]]
    allowed=lambda k:('.XCDAC.XS' in k and mode in ['ref','both']) or ('.XCOMP.' in k and mode in ['comp','both']) or (receiver and any(k.startswith('XDUT.XCTRL.XTIM.'+s+'.X000.') for s in ['X002','X003']))
    assert all(allowed(k) and original[k]['nodes']==devices[k]['nodes'] for k in changed)
    assert len(changed)==(32 if mode in ['ref','both'] else 0)+(11 if mode in ['comp','both'] else 0)+(4 if receiver else 0)
    mos={k:v for k,v in devices.items() if v['model'].startswith(('nch_','pch_'))}
    assert len(mos)==1833
    records=[];pairs=[];indices={}
    for name,v in mos.items():
        group=('bootstrap' if '.XBOOT' in name else 'reference' if '.XCDAC.' in name else
               'comparator' if '.XCOMP.' in name else 'reference_driver' if '.XREF.XDRV' in name else 'digital_control')
        ns=dict(zip('dgsb',v['nodes']))
        for a,b in ['ds','gs','gd','gb','bd','bs']:
            p=tuple(sorted([ns[a].lower(),ns[b].lower()]))
            if p not in indices:indices[p]=len(pairs);pairs.append(p)
            records.append(dict(instance=name,model=v['model'],group=group,terminal=a+b,nodes=p,
                                pair_index=indices[p],limit_v=.99 if v['model'] in ['nch_mac','pch_mac'] else 1.98))
    selected={"D%d"%b for b in range(8)}
    selected.update(['SAMPLE','VDD!','VINN','VINN_SRC','VINP','VINP_SRC','VREFN','VREFP',
        'XDUT.ACTIVE','XDUT.CMP_CLK','XDUT.COMP_N','XDUT.COMP_P','XDUT.PHI_U','XDUT.PRESET','XDUT.RST_DONE',
        'XDUT.SAMPLE_INT','XDUT.SAMPLE_MATCH','XDUT.SEQ_SAMPLE','XDUT.TOPN','XDUT.TOPP',
        'XDUT.XBOOTN.G','XDUT.XBOOTP.G','XDUT.XCTRL.PHI_W','XDUT.XREF.CAP_CLK'])
    selected.update('XDUT.G%s%d'%(s,b) for s in ['NN','NP','PN','PP'] for b in range(8))
    selected.update('XDUT.XCDAC.B%s%d'%(s,b) for s in ['N','P'] for b in range(8))
    selected.update('XDUT.XREF.%s%d'%(s,b) for s in ['H','L','Q','RST'] for b in range(8))
    selected.update('XDUT.XREF.XDRV%d.%s%s'%(b,g,suffix) for b,gs in [(3,['GPN','GPP']),(4,['GNN','GNP']),(7,['GPN','GPP'])]
                    for g in gs for suffix in ['A','B','DRV'])
    selected.update(['XDUT.XCOMP.X','XDUT.XCOMP.Y','XDUT.XCOMP.TAIL'])
    if receiver:
        selected.update('XDUT.XCTRL.XTIM.'+s for s in ['X002.N','X003.N','PR','NR','RAW','RAW_D','DEC','WRITE_REQ'])
        all_nodes={n.lower() for v in mos.values() for n in v['nodes']}
        assert all(('xdut.xctrl.xtim.'+s.lower()) in all_nodes for s in ['X002.N','X003.N','PR','NR','RAW','RAW_D','DEC','WRITE_REQ'])
    # Case-sensitive existing branch probes, no inserted voltage sources.
    currents={s+':1' for s in ['VVDD','VREFHIGH','VREFLOW','VSAMPLE','VVINP','VVINN']}
    products=[('VDD','vdd!','vvdd:1'),('REFP','vrefp_src','vrefhigh:1'),('REFN','vrefn_src','vreflow:1'),
              ('CLOCK','sample','vsample:1'),('INPUTP','vinp_src','vvinp:1'),('INPUTN','vinn_src','vvinn:1')]
    for name,v in mos.items():
        if '.XCOMP.' in name:
            for port,node in enumerate(v['nodes'],1):
                currents.add(name+':'+str(port))
                products.append((name.lower()+':'+str(port),node.lower(),name.lower()+':'+str(port)))
        if any(x in name for x in ['.XCDAC.XSP7.','.XCDAC.XSN4.','.XCDAC.XSP3.']):
            currents.update(name+':'+str(port) for port in range(1,5))
    selected.update(currents)
    selected.update(['VREFP_SRC','VREFN_SRC'])
    saves=selected|{n for v in mos.values() for n in v['nodes'] if n!='0'}
    events=['XDUT.CMP_CLK','XDUT.XCTRL.PHI_W','XDUT.PHI_U','XDUT.XREF.CAP_CLK',
            'XDUT.SEQ_SAMPLE','XDUT.SAMPLE_INT','XDUT.RST_DONE','XDUT.ACTIVE']
    events+=['XDUT.XREF.RST%d'%b for b in range(8)]
    seedtest=(seed/'test.scs').read_text()
    deck=seedtest.replace(old,'include "dut.scs"\n',1)
    assert deck.count('include "dut.scs"')==1
    deck=deck.replace('ffmacro_mos_moscap',process+'macro_mos_moscap').replace('SUP=0.99','SUP='+str(sup)).replace('temp=-40','temp='+str(temp))
    if reverse:
        waves={p:re.search(r'(?m)^VVIN'+p+r' .*?wave=(\[[^\n]+\])',deck)[1] for p in ['P','N']}
        for p in ['P','N']:
            deck=re.sub(r'(?m)(^VVIN'+p+r' .*?wave=)\[[^\n]+\]',lambda m:m[1]+waves['N' if p=='P' else 'P'],deck)
    if screen:
        assert deck.count('reltol=1e-6')==1
        deck=deck.replace('reltol=1e-6','reltol=1e-4')
    if stop_ns!=200:
        deck,n=re.subn(r'(tran_perf tran stop=)200n',r'\g<1>'+str(stop_ns)+'n',deck)
        assert n==1
    deck=re.sub(r'^save .*\n','',deck,flags=re.M)
    deck=deck.replace('saveOptions options save=selected','saveOptions options save=selected currents=selected subcktiprobes=no useprobes=no')
    deck+='\n'+'\n'.join('save '+s for s in sorted(saves))+'\n'
    for source in ['VSAMPLE','VVDD','VREFHIGH','VREFLOW','RREFP','RREFN','CREFP','CREFN','VVINP','VVINN','RINP','RINN']:
        if reverse and source in ['VVINP','VVINN']:continue
        assert re.findall('(?m)^'+source+r' .*',deck)==re.findall('(?m)^'+source+r' .*',seedtest)
    files={'dut.scs':dut,'test.scs':deck,'mapping.json':json.dumps(dict(records=records,pairs=pairs,stop_s=200e-9 if stop_ns==200 else stop_ns*1e-9),indent=2),
           'selected.txt':'\n'.join(s.lower() for s in sorted(selected))+'\n',
           'pairs.txt':'\n'.join(' '.join(p) for p in pairs)+'\n',
           'events.txt':'\n'.join(n.lower() for n in events)+'\n',
           'products.txt':'\n'.join(' '.join(p) for p in products)+'\n','stream.cpp':parser_source()}
    if verify_existing:
        for name,content in files.items():assert (folder/name).read_text()==content,name
        assert (folder/'r4_perf_monitor.va').read_bytes()==(seed/'r4_perf_monitor.va').read_bytes()
        print('REPRODUCTION_PASS',run,'unchanged inputs from committed circuit seed')
        return
    folder.mkdir(parents=True)
    for name,content in files.items():(folder/name).write_text(content)
    (folder/'r4_perf_monitor.va').write_bytes((seed/'r4_perf_monitor.va').read_bytes())
    inputs=[dict(source=(folder/f).relative_to(ROOT).as_posix(),name=f) for f in list(files)+['r4_perf_monitor.va']]
    inputs.append(dict(source='scripts/sar8_physical_repair/loaded_remote.py',name='loaded_remote.py'))
    recipe=dict(schema_version=1,run_id=run,design_id='sar8_loaded_tolerant_'+mode+suffix,entry='test.scs',inputs=inputs,
        analyzer='loaded_remote.py',summary_signals=['XDUT.CMP_CLK','XDUT.TOPP','XDUT.TOPN'],expected_stop_s=stop_ns*1e-9,
        qualification_scope='Two-frame real-load diagnosis, not qualification or baseline adoption',oa_parity='netlist_only',
        test_conditions=dict(corner=process,temperature_c=temp,vdd=sup,vrefp=.9,mode=mode,tail_units=tail,reset_units=reset,
                             sample_clock_unchanged=True,actual_aperture_to_verify=True,noise=False,mismatch=False,PEX=False,
                             requested_reltol=1e-4 if screen else 1e-6,numerical_screen_only=screen,pmos_latch_units=platch,receiver_n_units=receiver,reverse_input_order=reverse),
        resources=dict(threads=4,simulation_rss_mib=1024,simulation_virtual_mib=8192,analysis_rss_mib=256,
                       analysis_virtual_mib=1024,max_output_mib=32768,simulation_wall_seconds=3600,
                       analysis_wall_seconds=1800,queue_timeout_seconds=7200))
    (ROOT/'management/recipes'/(run+'.yaml')).write_text(yaml.safe_dump(recipe,sort_keys=False))
    manifest=dict(run_id=run,source_sha256=digest(seed/'dut.scs'),changed_instances=changed,changes=changes,
                  modes=mode,corner=corner,vdd=sup,temp_c=temp,MOS_count=len(mos),records=len(records),
                  saved_count=len(saves),selected_count=len(selected),files={f:digest(folder/f) for f in list(files)+['r4_perf_monitor.va']},
                  unchanged_connections=True,unchanged_other_devices=True,unchanged_external_sources=not reverse,
                  unchanged_sample_supply_reference_sources=True,reverse_input_order=reverse,
                  OA_changed=False,tail_units=tail,reset_units=reset,numerical_screen_only=screen,pmos_latch_units=platch,receiver_n_units=receiver,stop_ns=stop_ns)
    (ROOT/'verification/sar8_physical_repair'/(run+'_manifest.json')).write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({k:v for k,v in manifest.items() if k not in ['files','changed_instances']},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['base','ref','comp','both']);p.add_argument('corner',choices=CORNERS)
    p.add_argument('--tail',type=int,default=4);p.add_argument('--reset',type=int,default=2)
    p.add_argument('--verify-existing',action='store_true')
    p.add_argument('--screen',action='store_true')
    p.add_argument('--platch',type=int,default=2)
    p.add_argument('--receiver',type=int,default=0)
    p.add_argument('--reverse-inputs',action='store_true')
    p.add_argument('--stop-ns',type=int,choices=[200,210],default=200)
    a=p.parse_args();assert a.tail>0 and a.reset>0 and a.platch>0 and a.receiver>=0
    build(a.mode,a.corner,a.tail,a.reset,a.verify_existing,a.screen,a.platch,a.receiver,a.reverse_inputs,a.stop_ns)
