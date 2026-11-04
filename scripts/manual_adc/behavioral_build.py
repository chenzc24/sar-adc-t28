"""Build ONLY the manual ADC behavioral harness and one managed smoke recipe."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'verification/manual_adc/behavioral_v1'
RUN = 'manual8-beh-smoke-v2'


def pins(prefix):
    return ' '.join(prefix + str(i) for i in range(7, -1, -1))


def write(name, content):
    (BASE / name).write_text(content, encoding='utf-8')


def build():
    files = ['manual8_sample.va', 'manual8_cdac.va', 'manual8_cmp.va', 'manual8_sar.va']
    wrapper = 'simulator lang=spectre\n' + ''.join('ahdl_include "%s"\n' % f for f in files)
    wrapper += '''
// Interface-compatible wrappers. Select real/behavioral implementations here.
// Optional monitor pins are only on the behavioral ADC top, not the OA design.
subckt manual_cdac_beh CLKS GND VDD VIN VTOP VREFP VREFN DCTRL_7 DCTRL_6 DCTRL_5 DCTRL_4 DCTRL_3 DCTRL_2 DCTRL_1
parameters cunit=10f sample_ron=1 ref_ron=10 sample_qclk=0
XS (CLKS GND VDD VIN VTOP) manual8_sample ron=sample_ron qclk=sample_qclk
XD (GND VDD VTOP VREFP VREFN DCTRL_7 DCTRL_6 DCTRL_5 DCTRL_4 DCTRL_3 DCTRL_2 DCTRL_1) manual8_cdac cunit=cunit ron_unit=ref_ron
ends manual_cdac_beh

subckt manual_adc_beh CLKS GND VDD VINP VINN VREFP VREFN ''' + pins('DO_') + ''' BUSY EOC FAULT
parameters cunit=10f sample_ron=1 ref_ron=10 sample_qclk=0 cmp_td=200p cmp_vos=0 cmp_cin=0 cmp_edge=50p cmp_qkickp=0 cmp_qkickn=0 t_start=4n t_capture=50p t_update=100p t_settle=2n t_reset=500p t_timeout=8n logic_edge=50p
// Cross ONLY bit7, exactly as in the corrected native-derived candidate.
XP (CLKS GND VDD VINP TOPP VREFP VREFN DN_7 DP_6 DP_5 DP_4 DP_3 DP_2 DP_1) manual_cdac_beh cunit=cunit sample_ron=sample_ron ref_ron=ref_ron sample_qclk=sample_qclk
XN (CLKS GND VDD VINN TOPN VREFP VREFN DP_7 DN_6 DN_5 DN_4 DN_3 DN_2 DN_1) manual_cdac_beh cunit=cunit sample_ron=sample_ron ref_ron=ref_ron sample_qclk=sample_qclk
XC (CMPCK TOPP TOPN VDD GND DCMPP DCMPN) manual8_cmp td=cmp_td vos=cmp_vos cin=cmp_cin trf=cmp_edge qkickp=cmp_qkickp qkickn=cmp_qkickn
XL (CLKS GND VDD DCMPP DCMPN CMPCK ''' + pins('DO_') + ' ' + pins('DP_') + ' ' + pins('DN_') + ''' BUSY EOC FAULT) manual8_sar t_start=t_start t_capture=t_capture t_update=t_update t_settle=t_settle t_reset=t_reset t_timeout=t_timeout trf=logic_edge
ends manual_adc_beh
'''
    write('wrappers.scs', wrapper)
    codes = [0, 255, 85, 170, 127, 128, 1, 254]
    lsb = 1.8 / 256
    stimuli = {}
    for side in ['P', 'N']:
        points = []
        for j, code in enumerate(codes):
            dm = (code + .5) * lsb - .9
            value = .45 + (dm / 2 if side == 'P' else -dm / 2)
            if not j:
                points.append((0, value))
            else:
                # Input changes 10 ns before the next sample begins; previous
                # conversion has completed. Preserve the external clock edges.
                points.extend([(j*100, points[-1][1]), (j*100+.05, value)])
        stimuli[side] = ' '.join('%.12gn %.12g' % p for p in points)
    deck = '''simulator lang=spectre
global 0
include "wrappers.scs"
VVDD (VDD 0) vsource dc=.9
VREF (REF 0) vsource dc=.9
VCLK (CLKS 0) vsource type=pulse val0=0 val1=.9 delay=10n rise=50p fall=50p width=39.9n period=100n
'''
    deck += ''.join('VIN%s (VIN%s 0) vsource type=pwl wave=[%s]\n' % (side, side, stimuli[side]) for side in ['P','N'])
    deck += 'XADC (CLKS 0 VDD VINP VINN REF 0 '+pins('DO_')+' BUSY EOC FAULT) manual_adc_beh\n'
    experiment_deck = deck
    deck += '''
// Comparator cancellation probe: first CLK pulse ends before td; second is valid.
VCP (CP 0) vsource type=pwl wave=[0 0 2n 0 2.05n .9 2.4n .9 2.45n 0 4n 0 4.05n .9 6n .9 6.05n 0]
VIP (IP 0) vsource dc=.46
VIN (IN 0) vsource dc=.44
XCANCEL (CP IP IN VDD 0 COP CON) manual8_cmp td=1n
// Invalid comparator pair and missing-result timeout are explicit SAR faults.
VBAD (BAD 0) vsource type=pwl wave=[0 0 54.5n 0 54.55n .9 60n .9 60.05n 0]
'''
    for case, pp, nn in [('BAD','BAD','BAD'),('TIMEOUT','0','0')]:
        ports = ['CLKS','0','VDD',pp,nn,case+'CK']
        ports += [case+'_'+p+str(i) for p in ['DO','DP','DN'] for i in range(7,-1,-1)]
        ports += [case+'BUSY',case+'EOC',case+'FAULT']
        deck += 'X%s (%s) manual8_sar\n' % (case, ' '.join(ports))
    # Interrupt a real pending comparator operation by starting sampling early.
    deck += '''VABORT (ACLKS 0) vsource type=pwl wave=[0 0 10n 0 10.05n .9 49.95n .9 50n 0 54.1n 0 54.15n .9 89.95n .9 90n 0]
'''
    deck += 'XABORT (ACLKS 0 VDD IP IN REF 0 '+' '.join('ADO_'+str(i) for i in range(7,-1,-1))+' ABUSY AEOC AFAULT) manual_adc_beh\n'
    signals = ['VDD','VVDD:1','VINP','VINN','CLKS','BUSY','EOC','FAULT','COP','CON','CP',
               'BADFAULT','BADEOC','TIMEOUTFAULT','TIMEOUTEOC','ACLKS','ABUSY','AEOC','AFAULT','XABORT.CMPCK']
    signals += ['DO_'+str(i) for i in range(8)]
    signals += ['XADC.'+p for p in ['CMPCK','DCMPP','DCMPN','TOPP','TOPN']]
    signals += ['XADC.'+p+str(i) for p in ['DP_','DN_'] for i in range(8)]
    experiment_signals = ['VDD','VVDD:1','VINP','VINN','CLKS','BUSY','EOC','FAULT']
    experiment_signals += ['DO_'+str(i) for i in range(8)]
    experiment_signals += [s for s in signals if s.startswith('XADC.')]
    write('tb_adc.scs',experiment_deck+'''simulatorOptions options reltol=1e-6 vabstol=1e-8 iabstol=1e-14 temp=27 tnom=27
saveOptions options save=selected currents=selected
tran_test tran stop=820n maxstep=100p errpreset=conservative
save '''+' '.join(experiment_signals)+'\n')
    deck += '''simulatorOptions options reltol=1e-6 vabstol=1e-8 iabstol=1e-14 temp=27 tnom=27
saveOptions options save=selected currents=selected
tran_test tran stop=820n maxstep=100p errpreset=conservative
save '''+' '.join(signals)+'\n'
    write('tb_smoke.scs',deck)
    measure={'stop_s':820e-9,'signals':signals,'codes':codes,'lsb_V':lsb,'kind':'behavioral_smoke'}
    write('measure.json',json.dumps(measure,indent=2)+'\n')
    # Independent binary search oracle: first step rises in CM, later steps fall.
    for code in range(256):
        d=(code+.5)*lsb-.9; decoded=0; cm=.45
        for b in range(7,-1,-1):
            bit=int(d>=0);decoded|=bit<<b
            if b:
                step=.9*2**(b-1)/128
                d+=(-1 if bit else 1)*step
                cm+=(1 if b==7 else -1)*step/2
        assert decoded==code, (code,decoded)
        assert abs(d)<=lsb
        assert abs(cm-(.45+lsb/2))<1e-12
    inputs=[{'source':str((BASE/f).relative_to(ROOT)).replace('\\','/'),'name':f}
            for f in files+['wrappers.scs','tb_smoke.scs','measure.json']]
    inputs += [{'source':'scripts/manual_adc/behavioral_reduce.py','name':'behavioral_reduce.py'},
               {'source':'scripts/manual_adc/reduce.py','name':'reduce.py'}]
    recipe={'schema_version':1,'run_id':RUN,'design_id':'manual8_behavioral_v1','entry':'tb_smoke.scs',
            'analyzer':'behavioral_reduce.py','inputs':inputs,'expected_stop_s':820e-9,'summary_signals':signals,
            'qualification_scope':'VA compile, eight-code closed loop, charge redistribution, timer cancellation and fault diagnostics only; no transistor performance/PVT qualification',
            'oa_parity':'none; behavioral reference only; OA untouched',
            'test_conditions':{'corner':'behavioral_only','vdd':.9,'temperature_c':27,'noise':False,'mismatch':False,'PEX':False},
            'spectre_args':['+preset=cx','+mt=1','-preset_override'],
            'resources':{'threads':1,'simulation_rss_mib':1024,'simulation_virtual_mib':8192,
                         'analysis_rss_mib':256,'analysis_virtual_mib':1024,'max_output_mib':256,
                         'simulation_wall_seconds':600,'analysis_wall_seconds':300,'queue_timeout_seconds':600}}
    (ROOT/'management/recipes'/('%s.yaml'%RUN)).write_text(json.dumps(recipe,indent=2)+'\n')
    print('Built',RUN,'; independent 256-center-code oracle passed. No simulation launched.')


if __name__=='__main__':build()
