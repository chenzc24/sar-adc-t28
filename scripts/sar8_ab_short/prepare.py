"""Immutable paired TT stimulus/measurement, unchanged native DUTs."""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'verification/sar8_ab_short'
CODES=[0,0,12,127,128,243,255,255,0,128]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    sources={'a':'sar8_l90_mmain2_frozen','b':'sar8_l90_mmain2_stdcell_v1'}
    hashes={'a':'41d5444c4fcc3f26b097cca609474804afde2e61616c424c8a0cb8a5b2f298c4','b':'f31b66c8fb35003bf7e8ad1a23d9c230b39f1f9651ccc469953e5e52ecf493ea'}
    header=(ROOT/'netlist/sar8_physical/tt_nominal.scs').read_text().split('\ntran_physical')[0]
    header=header.replace('include "dut.scs"','include "library_include.scs"\ninclude "dut.scs"')
    header=header.replace('sensfile="../psf/sens.output" ','')
    tb=(ROOT/'netlist/sar8_physical/tb.scs').read_text()
    tb='\n'.join(s for s in tb.splitlines() if not s.startswith(('VVINP ','VVINN ')))+'\n'
    tb=tb.replace('VREFHIGH (VREFP_SRC 0) vsource dc=SUP','VREFHIGH (VREFP_SRC 0) vsource dc=0.9')
    for side,sign in [('P',1),('N',-1)]:
        vals=[.45+sign*(-.9+(k+.5)*1.8/256)/2 for k in CODES]
        points=[(0,vals[0])]
        for i in range(1,len(vals)):points.extend([(i*100+.8,vals[i-1]),(i*100+.9,vals[i])])
        points.append((1000,vals[-1]))
        tb+='VVIN%s (VIN%s_SRC 0) vsource type=pwl wave=[%s]\n'%(side,side,' '.join('%.12gn %.14g'%(t,v) for t,v in points))
    signals=['D%d'%i for i in range(8)]+['SAMPLE','VDD!','VINP_SRC','VINN_SRC','VINP','VINN','VREFP','VREFN',
        'XDUT.SAMPLE_INT','XDUT.SEQ_SAMPLE','XDUT.CMP_CLK','XDUT.XCTRL.PHI_W','XDUT.PHI_U','XDUT.XREF.CAP_CLK',
        'XDUT.TOPP','XDUT.TOPN','XDUT.XBOOTP.G','XDUT.XBOOTN.G','XDUT.ACTIVE','XDUT.COMP_P','XDUT.COMP_N']
    deck=header+'\nXMEASURE (XDUT.SAMPLE_INT XDUT.CMP_CLK XDUT.XCTRL.PHI_W XDUT.PHI_U XDUT.XREF.CAP_CLK VDD! VINP_SRC VINN_SRC XDUT.TOPP XDUT.TOPN D0 D1 D2 D3 D4 D5 D6 D7) r4_perf_monitor\n'
    deck+='ahdl_include "r4_perf_monitor.va"\ntran_ab tran stop=1000n maxstep=10p errpreset=conservative lteratio=10\nsave '+' '.join(signals)+'\n'
    runs=[]
    for label,design in sources.items():
        p=OUT/label;assert not p.exists();p.mkdir()
        src=ROOT/'netlist'/design/'dut.scs';assert sha(src)==hashes[label]
        (p/'test.scs').write_text(deck,encoding='utf-8');(p/'tb.scs').write_text(tb,encoding='utf-8')
        ctx=dict(label=label,expected_codes=CODES,frames=10,corner='tt',vdd=.9,temperature_c=27,reference_v=.9,
            LSB=1.8/256,period_s=1e-7,dut_sha256=hashes[label],signals=[s.lower() for s in signals],
            startup_frames=[0],settling_band_lsb=.25,noise=False,mismatch=False,PEX=False)
        dump(p/'context.json',ctx)
        paths=[src,p/'test.scs',p/'tb.scs',p/'context.json',ROOT/'netlist/sar8_l90_mmain2_stdcell_v1/library_include.scs',
            ROOT/'models/veriloga/sar8_r4_performance/r4_perf_monitor.va',ROOT/'scripts/sar8_ab_short/reduce.py']
        name='sar8ab-'+label+'-tt-short-v1';runs.append(name)
        recipe=dict(schema_version=1,run_id=name,design_id=design,entry='test.scs',analyzer='reduce.py',
            inputs=[dict(source=x.relative_to(ROOT).as_posix(),name=x.name,sha256=sha(x)) for x in paths],
            summary_signals=ctx['signals'],expected_stop_s=1e-6,test_conditions=ctx,
            qualification_scope='Paired TT function/aperture/handshake/settling; stress deferred',oa_parity='netlist_only',
            spectre_args=['+preset=cx','+mt=4','-preset_override','+lqtimeout','60'],
            resources=dict(threads=4,simulation_rss_mib=1024,simulation_virtual_mib=8192,analysis_rss_mib=256,
            analysis_virtual_mib=1024,max_output_mib=2048,simulation_wall_seconds=43200,analysis_wall_seconds=1200,queue_timeout_seconds=7200))
        dump(ROOT/'management/recipes'/(name+'.yaml'),recipe)
    assert (OUT/'a/test.scs').read_bytes()==(OUT/'b/test.scs').read_bytes()
    assert (OUT/'a/tb.scs').read_bytes()==(OUT/'b/tb.scs').read_bytes()
    dump(OUT/'batch.json',dict(runs=runs,identical_deck_stimulus=True,expected_codes=CODES))
    print(json.dumps(dict(runs=runs,identical_deck_stimulus=True)))
if __name__=='__main__':main()
