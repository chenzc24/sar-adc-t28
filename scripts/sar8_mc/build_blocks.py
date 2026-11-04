"""Native PDK CDAC and loaded-B-comparator module statistical fixtures."""
import hashlib,json,re
from pathlib import Path
R=Path(__file__).resolve().parents[2];V=R/'verification/sar8_mc/blocks'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2)+'\n', encoding='utf-8', newline='\r\n')
def logical(t):return re.sub(r'\\\n\s*',' ',t)

def main():
    dut=R/'netlist/sar8_l90_mmain2_stdcell_v1/dut.scs'
    assert sha(dut)=='f31b66c8fb35003bf7e8ad1a23d9c230b39f1f9651ccc469953e5e52ecf493ea'
    text=dut.read_text();blocks={m.group(1):m.group() for m in re.finditer(r'(?ms)^subckt (\w+)\b.*?^ends \1\b',text)}
    header=(V/'fixture_header.scs').read_text()
    for x,y in [('ttmacro_mos_moscap','TTGlobalCorner_LocalMC_MOS_MOSCAP'),('tt_mom','TTGlobalCorner_LocalMC_MOM')]:header=header.replace('section='+x,'section='+y)
    options='\nsimulatorOptions options temp=27 tnom=27 reltol=1e-6 vabstol=1e-8 iabstol=1e-13 method=trap maxwarns=5 maxnotes=5 preserve_inst=all\nsaveOptions options save=selected\n'
    momlines=[x.strip() for x in logical(blocks['sar8j_r1_cdac']).splitlines() if re.match(r'\s*CMOM[PN]\d',x)]
    assert len(momlines)==18
    caps=[];signals=[]
    for x in momlines:
        m=re.match(r'(CMOM([PN])(\d)) \([^)]*\) (.+)',x);assert m
        name,side,bit,params=m.groups();caps+=['V%s (%s 0) vsource dc=0.45 mag=1'%(name,name),'%s (%s 0) %s'%(name,name,params)];signals.append('v'+name.lower()+':p')
    cdac='\n'.join(caps)+'\n'
    roots=['sar_strongarm_t28','sar8p_buf','sar8p_inv','sar8p_and2','sar8p_xor2','sar8p_delay_valid'];needed=set()
    def add(name):
        if name in needed:return
        needed.add(name)
        for line in logical(blocks[name]).splitlines():
            m=re.match(r'\s*X\w+ \([^)]*\)\s+(\w+)',line)
            if m and m[1] in blocks:add(m[1])
    for name in roots:add(name)
    part='\n\n'.join(blocks[k] for k in sorted(needed))+'\n'
    top=logical(blocks['sar_adc8_join_r4']);loads=[]
    for line in top.splitlines():
        if re.match(r'\s*CL_COMP_[NP] ',line):loads.append(line.strip().replace('COMP_N','ON').replace('COMP_P','OP'))
    assert len(loads)==2
    fixture='''
VVDD (SUP 0) vsource dc=0.9
VCLOCK (CLK 0) vsource type=pulse val0=0 val1=0.9 delay=2n rise=50p fall=50p width=1.95n period=5n
XCMP (CLK ON OP SUP VINN VINP 0) sar_strongarm_t28
XRXN (ON SUP 0 NR) sar8p_buf
XRXP (OP SUP 0 PR) sar8p_buf
XNRB (NR SUP 0 NRB) sar8p_inv
XDATA (PR NRB SUP 0 DATA) sar8p_and2
XRAW (PR NR SUP 0 RAW) sar8p_xor2
XDELAY (RAW SUP 0 RAW_D) sar8p_delay_valid
CDATA (DATA 0) capacitor c=5f
XSEARCH (VINP VINN OP ON PR NR CLK SUP 0) sar8_mc_comp_search
ahdl_include "comp_search.va"
'''+ '\n'.join(loads)+'\n'
    manifest={'source_dut_sha256':sha(dut),'runs':{},'concurrency':4,'seeds':list(range(4101,4131)),
        'scope':'Independent module mismatch characterization, no integrated yield or stress qualification',
        'comparator_boundary':'B core+native output MOM+two original buffers+original PR/NR logic loads; DATA register bank omitted, not full handshake',
        'clock_scope':'5ns period/2ns high diagnostic search; report delay at actual B shorter clock windows separately',
        'B_native_cmp_high_ns_reference':[0.7977,1.0052],
        'component_hashes':{k:hashlib.sha256(blocks[k].encode()).hexdigest() for k in needed}}
    for family in ['cdac','comp']:
      for tag,seed in [('nominal',None)]+[('s%d'%s,s) for s in range(4101,4131)]+[('s4101-repeat',4101)]:
        run='sar8mc-'+family+'-'+tag+'-v2';p=V/run;p.mkdir(parents=True,exist_ok=False)
        c={'run_id':run,'family':family,'seed':seed,'mismatch':seed is not None,'process_variation':False,'noise':False,
            'vdd':.9,'temperature_c':27,'cm':.45,'scope':manifest['scope'],'parent_dut_sha256':sha(dut)}
        body=header+options
        extras=[]
        if family=='cdac':
            body+=cdac;child='cap_ac ac start=1Meg stop=2Meg lin=2';save_signals=signals
            c.update(bias_v=.45,frequency_hz=1e6,nominal_cap_units=512,instances=18,static_scope='AC effective binary capacitor weights at one bias; not dynamic CDAC/ADC DNL signoff')
            stop=1e-12
        else:
            body+='include "library_include.scs"\n'+part+fixture
            child='comp_tran tran stop=109n maxstep=5p errpreset=conservative'
            save_signals=['op','on','pr','nr','clk','vinp','vinn','xcmp.x','xcmp.y','xcmp.tail']
            c.update(cycles=22,period_s=5e-9,report_s=3.775e-9,search_steps=10,search_range_v=.064,stop_s=109e-9,threshold_window_s=1.75e-9)
            stop=109e-9
            for path,name in [(R/'netlist/sar8_l90_mmain2_stdcell_v1/library_include.scs','library_include.scs'),(R/'scripts/sar8_mc/comp_search.va','comp_search.va')]:extras.append((path,name))
        if seed is not None:body+='mc montecarlo numruns=1 seed=%d variations=mismatch sampling=standard donominal=no savemismatchparams=yes mismatchparamfile="mismatch.params" mismatchscalarfile="mismatch.values" savefamilyplots=yes savedatainseparatedir=yes {\n%s\n}\n'%(seed,child)
        else:body+=child+'\n'
        c.update(fixture_revision=2,preserve_inst='all')
        if family=='cdac':c['previous_fixture_statistically_invalid']=True
        names=[x.split(':')[0].upper()+':p' if ':' in x else x.upper() for x in save_signals]
        body+='save '+' '.join(names)+'\n';(p/'test.scs').write_text(body, encoding='utf-8', newline='\r\n');save(p/'context.json',c)
        inputs=[(p/'test.scs','test.scs'),(p/'context.json','context.json'),(R/'scripts/sar8_mc/block_reduce.py','block_reduce.py'),(R/'scripts/sar8_campaign/native_stream.py','native_stream.py')]+extras
        rec={'schema_version':1,'run_id':run,'design_id':'sar8_l90_mmain2_stdcell_v1','entry':'test.scs','analyzer':'block_reduce.py',
            'inputs':[{'source':q.relative_to(R).as_posix(),'name':n,'sha256':sha(q)} for q,n in inputs],
            'summary_signals':save_signals,'expected_stop_s':stop,'test_conditions':c,'qualification_scope':manifest['scope'],
            'spectre_args':['+preset=mx','+mt=4','-preset_override','+lqtimeout','60'],
            'resources':{'threads':4,'simulation_rss_mib':1024,'simulation_virtual_mib':8192,'analysis_rss_mib':256,'analysis_virtual_mib':1024,'max_output_mib':256,'simulation_wall_seconds':7200,'analysis_wall_seconds':600,'queue_timeout_seconds':86400}}
        save(R/'management/recipes'/(run+'.yaml'),rec);manifest['runs'][family+'-'+tag]={'run_id':run,'seed':seed,'family':family}
    manifest.update(fixture_revision=2, supersedes='v1 CDAC independent sampling invalid due turbo merge; v1 comparator target input pair was independent')
    save(V/'v2_manifest.json',manifest);print('Prepared',len(manifest['runs']),'module fixtures')
if __name__=='__main__':main()
