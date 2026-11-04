"""Bootstrap-only mixed-level short tests. No OA or source-candidate changes."""
import hashlib,json,re,shutil
from pathlib import Path
R=Path(__file__).resolve().parents[2]
B=R/'verification/manual_adc';OUT=B/'bootstrap_short_v1'

def write(p,s):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding='utf-8')
def pins(p):return ' '.join(p+str(i) for i in range(7,-1,-1))
def pulse(name,node):return '%s (%s 0) vsource type=pulse val0=0 val1=.9 delay=10n rise=50p fall=50p width=39.9n period=100n\n'%(name,node)

def build():
    source=(B/'candidate_io_v1/dut.scs').read_text()
    boot='subckt manual_boot '+source.split('subckt manual_boot ',1)[1].split('ends manual_boot',1)[0]+'ends manual_boot\n'
    mos=re.findall(r'^(M\w+) \(([^)]+)\) (\w+)',boot,re.M)
    assert len(mos)==12 and all(m[2] in ['nch_18_mac','pch_18_mac'] for m in mos)
    models=(B/'joined_dc_v1/models.scs').read_text().split('simulator lang=spice')[0]
    va=B/'behavioral_v1';vhash=json.loads((va/'validation.json').read_text())['source_sha256']
    for f,h in vhash.items():assert hashlib.sha256((va/f).read_bytes()).hexdigest()==h
    original=(va/'wrappers.scs').read_text()
    hybrid=original[original.index('// Interface-compatible'):].replace('manual_cdac_beh','manual_cdac_boot').replace('manual_adc_beh','manual_adc_boot')
    hybrid=hybrid.replace('XS (CLKS GND VDD VIN VTOP) manual8_sample ron=sample_ron qclk=sample_qclk','XS (CLKS GND VDD VIN VTOP) manual_boot main_mult=4')
    hybrid='simulator lang=spectre\ninclude "models.scs"\ninclude "boot.scs"\ninclude "wrappers_ideal.scs"\n'+hybrid
    cases={'dc':{'codes':[7,248,128,64,192,1,254,127]},'startup':{'codes':[7,248,7,248]},'sine':{'frames':16}}
    for name,spec in cases.items():
        p=OUT/name;p.mkdir(parents=True,exist_ok=True)
        for f in vhash:shutil.copyfile(va/f,p/f)
        write(p/'boot.scs','simulator lang=spectre\n'+boot)
        write(p/'models.scs',models);write(p/'wrappers_ideal.scs',original);write(p/'wrappers_hybrid.scs',hybrid)
        n=spec.get('frames',len(spec.get('codes',[])));freq=10e6*461/1024;amp=.9*10**(-1/20)
        ramp=name=='startup'
        deck='simulator lang=spectre\nglobal 0\ninclude "wrappers_hybrid.scs"\n'
        for src,node in [('VVDD','VDD'),('VVDDH','VDDH'),('VREF','REF')]:
            deck+='%s (%s 0) vsource '%(src,node)+('type=pwl wave=[0 0 1n .9]\n' if ramp else 'dc=.9\n')
        deck+=pulse('VCLK','CLKS')+pulse('VCLKH','CLKH')
        for side in ['P','N']:
            if name=='sine':
                deck+='VIN%s (VIN%s 0) vsource type=sine sinedc=.45 ampl=%.14g freq=%.14g\n'%(side,side,amp/2*(1 if side=='P' else -1),freq)
            else:
                pts=[]
                for j,c in enumerate(spec['codes']):
                    diff=(c+.5)*1.8/256-.9;val=.45+diff/2*(1 if side=='P' else -1)
                    if j==0:pts=([(0,0),(1,val)] if ramp else [(0,val)])
                    else:pts.extend([(j*100,pts[-1][1]),(j*100+.05,val)])
                deck+='VIN%s (VIN%s 0) vsource type=pwl wave=[%s]\n'%(side,side,' '.join('%.12gn %.14g'%z for z in pts))
        deck+='VSENP (VINP INP) vsource dc=0\nVSENN (VINN INN) vsource dc=0\n'
        deck+='XADC (CLKS 0 VDD INP INN REF 0 '+pins('DO_')+' BUSY EOC FAULT) manual_adc_boot ref_ron=.01\n'
        deck+='XIDEAL (CLKS 0 VDD VINP VINN REF 0 '+pins('IDO_')+' IBUSY IEOC IFAULT) manual_adc_beh ref_ron=.01\n'
        deck+='''// Companion fixture isolates turnoff/hold from intentional DAC redistribution.
XHP (CLKH 0 VDDH VINP HP) manual_boot main_mult=4
XHN (CLKH 0 VDDH VINN HN) manual_boot main_mult=4
CHP (HP 0) capacitor c=1.28p
CHN (HN 0) capacitor c=1.28p
'''
        signals=set(['VDD','VDDH','REF','VVDD:1','VVDDH:1','VCLK:1','VCLKH:1','VSENP:1','VSENN:1',
                     'VINP','VINN','INP','INN','CLKS','CLKH','HP','HN','BUSY','EOC','FAULT','IEOC','IFAULT'])
        signals.update('DO_'+str(i) for i in range(8));signals.update('IDO_'+str(i) for i in range(8))
        signals.update(x+'.'+s for x in ['XADC','XIDEAL'] for s in ['TOPP','TOPN','CMPCK'])
        signals.update('XADC.'+s+str(i) for s in ['DP_','DN_'] for i in range(8))
        devs=[]
        instances=[('XADC.XP.XS',{'CLKS':'CLKS','GND':'0','VDD':'VDD','VIN':'INP','VOUT':'XADC.TOPP'}),
                   ('XADC.XN.XS',{'CLKS':'CLKS','GND':'0','VDD':'VDD','VIN':'INN','VOUT':'XADC.TOPN'}),
                   ('XHP',{'CLKS':'CLKH','GND':'0','VDD':'VDDH','VIN':'VINP','VOUT':'HP'}),
                   ('XHN',{'CLKS':'CLKH','GND':'0','VDD':'VDDH','VIN':'VINN','VOUT':'HN'})]
        for path,mapping in instances:
            for mid,nodes,model in mos:
                terms=[mapping.get(x,path+'.'+x) for x in nodes.split()]
                devs.append({'path':path+'.'+mid,'model':model,'terminals':terms})
                signals.update(x for x in terms if x!='0')
        stop=(n*100+20)*1e-9
        deck+='simulatorOptions options reltol=1e-6 vabstol=1e-8 iabstol=1e-14 temp=27 tnom=27\nsaveOptions options save=selected currents=selected\n'
        deck+='tran_test tran stop=%.14g maxstep=50p errpreset=conservative\nsave '%stop+' '.join(sorted(signals))+'\n'
        write(p/'test.scs',deck)
        cfg={'case':name,'frames':n,'stop_s':stop,'codes':spec.get('codes'),'signals':sorted(signals),'devices':devs,
             'freq_Hz':freq,'differential_amplitude_V':amp,'lsb_V':1.8/256,'terminal_screen_V':1.98,
             'sample_close0_s':49.975e-9,'sample_open0_s':10.025e-9,'period_s':100e-9,
             'boot_sha256':hashlib.sha256(boot.encode()).hexdigest(),'behavioral_source_sha256':vhash,
             'budgets':{'static_preclose_LSB':.1,'held_diff_LSB':.25,'quiet_hold_LSB':.05,'input_feedthrough_LSB':.25,'sine_fit_peak_LSB':.25,'precharge_fraction':.95,'VDD_plus_clock_W':100e-6}}
        write(p/'measure.json',json.dumps(cfg,indent=2)+'\n')
        run='manual8-bootshort-'+name+'-v1'
        inputs=[{'source':str(f.relative_to(R)).replace('\\','/'),'name':f.name} for f in sorted(p.iterdir()) if f.suffix in ['.va','.scs','.json']]
        inputs += [{'source':'scripts/manual_adc/bootstrap_short_reduce.py','name':'bootstrap_short_reduce.py'},{'source':'scripts/manual_adc/reduce.py','name':'reduce.py'}]
        recipe={'schema_version':1,'run_id':run,'design_id':'manual8_bootstrap_only_hybrid_v1','entry':'test.scs','analyzer':'bootstrap_short_reduce.py','inputs':inputs,
                'expected_stop_s':stop,'summary_signals':['CLKS','VINP','VINN','XADC.TOPP','XADC.TOPN','EOC','FAULT'],
                'qualification_scope':'Unchanged IO bootstrap only, other modules behavioral, short nominal diagnostic; no PVT/FFT/lifetime claim',
                'oa_parity':'netlist_only; OA unchanged','test_conditions':{'corner':'tt','vdd':.9,'temperature_c':27,'noise':False,'mismatch':False,'PEX':False,'startup_supply_ramp_s':1e-9 if ramp else None},
                'spectre_args':['+preset=cx','+mt=1','-preset_override'],
                'resources':{'threads':1,'simulation_rss_mib':1024,'simulation_virtual_mib':8192,'analysis_rss_mib':256,'analysis_virtual_mib':1024,'max_output_mib':512,'simulation_wall_seconds':900,'analysis_wall_seconds':900,'queue_timeout_seconds':900}}
        write(R/'management/recipes'/('%s.yaml'%run),json.dumps(recipe,indent=2)+'\n')
        print(run,'frames',n,'MOS',len(devs),'saved',len(signals))

if __name__=='__main__':build()
