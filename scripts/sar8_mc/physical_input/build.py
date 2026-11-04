"""Prepare paired stiff/physical hold fixtures with preserved comparator hierarchy."""
import hashlib,json,re
from pathlib import Path
R=Path(__file__).resolve().parents[3];V=R/'verification/sar8_mc/physical_input';S=R/'scripts/sar8_mc/physical_input'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def logical(t):return re.sub(r'\\\n\s*',' ',t)
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2)+'\n')
def main():
    dut=R/'netlist/sar8_l90_mmain2_stdcell_v1/dut.scs';assert sha(dut)=='f31b66c8fb35003bf7e8ad1a23d9c230b39f1f9651ccc469953e5e52ecf493ea'
    text=dut.read_text();blocks={m[1]:m[0] for m in re.finditer(r'(?ms)^subckt (\w+)\b.*?^ends \1\b',text)}
    old=(R/'verification/sar8_mc/blocks/sar8mc-comp-s4124-v2/test.scs').read_text()
    ref=json.loads((R/'output/managed_execution/runs/sar8phys-clock-reference-v1/collected/derived/result.json').read_text())
    rise,fall=[x[0] for x in ref['events']['xdut.cmp_clk'][:2]];report=fall-50e-12;pre=rise-100e-12
    clock=[]
    for name,node,inst in [('sample','SAMPLE','VEXT'),('xdut.seq_sample','SAMPLE_HOLD','VBOOT'),('xdut.cmp_clk','CLK','VCLOCK')]:
        q=ref['traces'][name];points=[]
        for frame in range(22):
            for t,v in q:
                if frame and t<59e-9:continue
                nt=t+frame*100e-9
                if not points or nt>points[-1][0]:points.append((nt,v))
        points.append((2259e-9,points[-1][1]))
        clock.append('%s (%s 0) vsource type=pwl wave=[ \\'%(inst,node))
        for j in range(0,len(points),4):clock.append(' '.join('%.16g %.16g'%p for p in points[j:j+4])+' \\')
        clock.append(']')
    clock_path=V/'clock_sources.scs';clock_path.write_text('\n'.join(clock)+'\n')
    needed=set()
    def add(n):
        if n in needed:return
        needed.add(n)
        for line in logical(blocks[n]).splitlines():
            m=re.match(r'\s*X\w+ \([^)]*\)\s+(\w+)',line)
            if m and m[1] in blocks:add(m[1])
    for n in ['sar_bootstrap_flat_8b_p','sar8j_r1_cdac']:add(n)
    original_definitions=set(re.findall(r'(?m)^subckt (\w+)',old));new_defs='\n\n'.join(blocks[k] for k in sorted(needed-original_definitions))
    gatesN=['VDD!']*16;gatesP=['0']*16
    hold='''
// Added front-end is nominal under MC ignore=[XHOLD], preserving original samples.
subckt sar8_phys_hold SAMPLE SIP SIN TOPP TOPN VREFP VREFN VDD VSS
  RIP (SIP IP) resistor r=50
  RIN (SIN IN) resistor r=50
  XBOOTP (SAMPLE TOPP IP) sar_bootstrap_flat_8b_p
  XBOOTN (SAMPLE TOPN IN) sar_bootstrap_flat_8b_p
  XCDAC ('''+ ' '.join(gatesN+gatesP)+''' TOPN TOPP VDD VREFN VREFP VSS) sar8j_r1_cdac
ends sar8_phys_hold
'''
    base=old[:old.index('VVDD')]+new_defs+'\n'+hold
    fixture=old[old.index('VVDD'):old.index('mc montecarlo')]
    fixture=re.sub(r'(?m)^VCLOCK.*\n','include "clock_sources.scs"\n',fixture)
    fixture=fixture.replace('XSEARCH (VINP VINN OP ON PR NR CLK SUP 0) sar8_mc_comp_search',
      'XSEARCH (SIP SIN VINP VINN OP ON PR NR CLK SUP 0) sar8_phys_search cm=0.45 first_report_s=%.17g first_pre_s=%.17g'%(report,pre))
    fixture=fixture.replace('ahdl_include "comp_search.va"','ahdl_include "held_search.va"')
    fixture+='''
VGLOBAL (VDD! 0) vsource dc=0.9
VREFHI (RP_SRC 0) vsource dc=0.9
VREFLO (RN_SRC 0) vsource dc=0
RRP (RP_SRC RP) resistor r=50
RRN (RN_SRC RN) resistor r=50
CRP (RP 0) capacitor c=4p
CRN (RN 0) capacitor c=4p
XHOLD (SAMPLE_HOLD SIP SIN VINP VINN RP RN SUP 0) sar8_phys_hold
RCLAMPP (SIP VINP) resistor r=RCLAMP
RCLAMPN (SIN VINN) resistor r=RCLAMP
'''
    sig=['OP','ON','PR','NR','CLK','VINP','VINN','SIP','SIN','SAMPLE','SAMPLE_HOLD','XHOLD.XBOOTP.G','XHOLD.XBOOTN.G','XHOLD.IP','XHOLD.IN','XCMP.X','XCMP.Y','XCMP.TAIL']
    manifest={'parent_dut_sha256':sha(dut),'samples':[None,4121,4124],'runs':{},'clock_source_run':'sar8phys-clock-reference-v1','first_rise_s':rise,'first_fall_s':fall,'first_report_s':report,'first_pre_s':pre,
      'scope':'First-comparison threshold plus repeated native eight-pulse burst, static N-low/P-high bottom word; nominal real front-end; not full SAR feedback'}
    for seed in [None,4121,4124]:
      for mode in ['stiff','hold']:
        tag='nominal' if seed is None else 's%d'%seed;run='sar8phys-'+tag+'-'+mode+'-v2';p=V/run;p.mkdir(exist_ok=False)
        ctx={'run_id':run,'seed':seed,'mode':mode,'vdd':.9,'temperature_c':27,'cm_source_v':.45,'period_s':100e-9,'cycles':22,'search_steps':10,'search_range_v':.064,
          'report_s':report,'pre_s':pre,'first_clock_rise_s':rise,'first_clock_fall_s':fall,'threshold_window_s':report-rise,'stop_s':2259e-9,
          'RCLAMP_ohm':1e-3 if mode=='stiff' else 1e18,'parent_dut_sha256':sha(dut),'scope':manifest['scope'],'front_end_mismatch':False}
        if seed:
            expected=json.loads((R/'output/sar8_mc/physical_input'/('sample%d.json'%seed)).read_text());save(p/'expected_mismatch.json',expected)
        else:save(p/'expected_mismatch.json',{'rows':{},'columns':[],'source_run_id':'sar8mc-comp-nominal-v2'})
        body=base+'parameters RCLAMP=%.17g\n'%ctx['RCLAMP_ohm']+fixture
        child='phys_tran tran stop=2259n maxstep=5p errpreset=conservative'
        if seed:body+='mc montecarlo numruns=1 seed=%d variations=mismatch sampling=standard donominal=no ignore=[XHOLD] savemismatchparams=yes mismatchparamfile="mismatch.params" mismatchscalarfile="mismatch.values" savefamilyplots=yes savedatainseparatedir=yes {\n%s\n}\n'%(seed,child)
        else:body+=child+'\n'
        body+='save '+' '.join(sig)+'\n';(p/'test.scs').write_text(body);save(p/'context.json',ctx)
        files=[(p/'test.scs','test.scs'),(p/'context.json','context.json'),(p/'expected_mismatch.json','expected_mismatch.json'),(clock_path,'clock_sources.scs'),
          (S/'held_search.va','held_search.va'),(S/'reduce.py','reduce.py'),(R/'scripts/sar8_campaign/native_stream.py','native_stream.py'),(R/'netlist/sar8_l90_mmain2_stdcell_v1/library_include.scs','library_include.scs')]
        spec={'schema_version':1,'run_id':run,'design_id':'sar8_l90_mmain2_stdcell_v1','entry':'test.scs','analyzer':'reduce.py',
          'inputs':[{'source':x.relative_to(R).as_posix(),'name':n,'sha256':sha(x)} for x,n in files],'summary_signals':sig,'expected_stop_s':ctx['stop_s'],'test_conditions':ctx,
          'qualification_scope':manifest['scope'],'spectre_args':['+preset=mx','+mt=4','-preset_override','+lqtimeout','60'],
          'resources':{'threads':4,'simulation_rss_mib':1024,'simulation_virtual_mib':8192,'analysis_rss_mib':256,'analysis_virtual_mib':1024,'max_output_mib':512,'simulation_wall_seconds':14400,'analysis_wall_seconds':1200,'queue_timeout_seconds':86400}}
        save(R/'management/recipes'/(run+'.yaml'),spec);manifest['runs'][run]=ctx
    save(V/'manifest_v2.json',manifest);print('Prepared',len(manifest['runs']),'paired fixtures; clock points preserved, first window ns',(report-rise)*1e9)
if __name__=='__main__':main()
