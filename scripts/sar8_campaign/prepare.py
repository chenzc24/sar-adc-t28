"""Prepare immutable future cases locally; execution remains conditional."""
import hashlib,json,re
from pathlib import Path
R=Path(__file__).resolve().parents[2];V=R/'verification/sar8_campaign';S=R/'scripts/sar8_campaign'
POINTS=[('tt','tt',.9,27),('ssc','ss',.81,-40),('ssh','ss',.81,125),('ffc','ff',.99,-40),('ffh','ff',.99,125)]
RANGES=[(1,3)]+[(x,min(x+31,255)) for x in range(4,256,32)]
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    V.mkdir(exist_ok=True);manifest=dict(labels={},points=POINTS,stats_gate='Pending statistical model and capacitor unit/multi audit')
    for label in ['a','b']:
        base=R/'verification/sar8_ab_phase60'/label
        old=json.loads((R/'management/recipes'/('sar8ab-phase60-'+label+'-tt-v1.yaml')).read_text())
        dut=next(R/x['source'] for x in old['inputs'] if x['name']=='dut.scs')
        lib=next(R/x['source'] for x in old['inputs'] if x['name']=='library_include.scs')
        head=(base/'test.scs').read_text().split('\nXMEASURE')[0]
        rawtb=(base/'tb.scs').read_text();baretb='\n'.join(x for x in rawtb.splitlines() if not x.startswith(('VVINP ','VVINN ')))+'\n'
        mon=(base/'test.scs').read_text().split('\nXMEASURE')[1].split('\nahdl_include')[0]
        mon='XMEASURE'+mon+'\nahdl_include "r4_perf_monitor.va"\n'
        manifest['labels'][label]=dict(dut_sha256=sha(dut),points={})
        for point,corner,sup,temp in POINTS:
            h=head.replace('SUP=0.9','SUP='+str(sup)).replace('temp=27 ','temp='+str(temp)+' ')
            h=h.replace('section=ttmacro_mos_moscap','section='+corner+'macro_mos_moscap')
            entry=manifest['labels'][label]['points'][point]=dict(static=[])
            def case(run,kind,ctx,deck,tb,analyzer,extra=(),dynamic=False):
                folder=V/run;folder.mkdir()
                ctx.update(run_id=run,kind=kind,label=label,dut_sha256=sha(dut),corner=corner,vdd=sup,temperature_c=temp,
                    reference_v=.9,frame_origin_s=59e-9,noise=False,mismatch=False,PEX=False,passive_corner='nominal_tt')
                for n,t in [('test.scs',deck),('tb.scs',tb)]: (folder/n).write_text(t)
                write(folder/'context.json',ctx)
                paths=[folder/'test.scs',folder/'tb.scs',folder/'context.json',dut,lib,S/'r4_perf_monitor.va',S/analyzer]+list(extra)
                if len({p.name for p in paths})!=len(paths):raise ValueError('Duplicate input name')
                rec=dict(schema_version=1,run_id=run,design_id=old['design_id'],entry='test.scs',analyzer=analyzer,
                    inputs=[dict(source=p.relative_to(R).as_posix(),name=p.name,sha256=sha(p)) for p in paths],
                    summary_signals=ctx['signals'],expected_stop_s=ctx['stop_s'],test_conditions=ctx,
                    qualification_scope='Conditional frozen functional characterization; stress deferred',oa_parity='netlist_only',
                    spectre_args=old['spectre_args'],resources=dict(threads=4,simulation_rss_mib=1024,
                        simulation_virtual_mib=8192,analysis_rss_mib=256,analysis_virtual_mib=1024,
                        max_output_mib=16384 if dynamic else 2048,simulation_wall_seconds=345600 if dynamic else 172800,
                        analysis_wall_seconds=7200 if dynamic else 1800,queue_timeout_seconds=86400))
                write(R/'management/recipes'/(run+'.yaml'),rec)
            if point!='tt':
                run='sar8camp-'+label+'-'+point+'-screen-v1';entry['screen']=run
                ctx=json.loads((base/'context.json').read_text());ctx['stop_s']=ctx['expected_stop_s']
                # Replace only process/temp/supply header; the observer/signals are identical.
                deck=(base/'test.scs').read_text().replace(head,h)
                case(run,'screen',ctx,deck,rawtb,'screen_reduce.py')
            for first,last in RANGES:
                run='sar8camp-%s-%s-s%03d-%03d-v1'%(label,point,first,last);entry['static'].append(run)
                frames=4+(last-first+1)*10+1;stop_ns=59+frames*100
                sig=['D%d'%b for b in range(8)]+['SAMPLE','VDD!','XDUT.SAMPLE_INT','XDUT.CMP_CLK','XDUT.TOPP','XDUT.TOPN','VINP_SRC','VINN_SRC']
                deck=h+'\nXSTIM (VINP_SRC VINN_SRC D0 D1 D2 D3 D4 D5 D6 D7) r4_transition_stim time_origin=59n first_k=%d last_k=%d warmup=4 refine=7 half_span_lsb=0.5\n'%(first,last)+mon
                deck+='ahdl_include "r4_transition_stim.va"\ntran_perf tran stop=%dn maxstep=10p errpreset=conservative lteratio=10 strobeperiod=1n strobeoutput=strobeonly\nsave %s\n'%(stop_ns,' '.join(sig))
                ctx=dict(first=first,last=last,frames=frames,warmup=4,refine=7,stop_s=stop_ns*1e-9,signals=[s.lower() for s in sig],fullscale_v=1.8)
                case(run,'static',ctx,deck,baretb,'static_reduce.py',[S/'r4_transition_stim.va'])
            if point=='tt':
                run='sar8camp-'+label+'-tt-fft1024-v1';entry['dynamic']=run
                warm=8;frames=warm+1024;stop_ns=59+frames*100;freq=1e7*461/1024;amp=.9*10**(-1/20)
                tb=baretb
                for side,sign in [('P',1),('N',-1)]:
                    phase=(-360*freq*59e-9+(0 if sign==1 else 180))%360
                    tb+='VVIN%s (VIN%s_SRC 0) vsource type=sine dc=.45 sinedc=.45 ampl=%.16g freq=%.16g sinephase=%.16g\n'%(side,side,amp/2,freq,phase)
                sig=['D%d'%b for b in range(8)]+['SAMPLE','VDD!','VINP_SRC','VINN_SRC','VVDD:p','VREFHIGH:p','VREFLOW:p','VSAMPLE:p']
                deck=h+'\n'+mon+'tran_perf tran stop=%dn maxstep=10p errpreset=conservative lteratio=10 strobeperiod=10p strobeoutput=strobeonly\nsave %s\n'%(stop_ns,' '.join(sig))
                ctx=dict(frames=frames,warmup=warm,stop_s=stop_ns*1e-9,signals=[s.lower() for s in sig],frequency_hz=freq,samples=1024,bin=461,amplitude_dbfs=-1)
                case(run,'dynamic',ctx,deck,tb,'dynamic_reduce.py',[S/'native_stream.py'],dynamic=True)
    write(V/'manifest.json',manifest)
    print('Prepared',len(list(V.glob('sar8camp-*'))),'future cases; none submitted by prepare.')
if __name__=='__main__':main()
