"""Freeze local read-only sources and generate receiver-load measurement."""
import hashlib,json,re,sys
from pathlib import Path
W=Path(__file__).resolve().parents[1]
ROOT=W.parent

def write(path,text):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding='utf-8')

def recipe(run,folder,signals,stop,analyzer,conditions=None):
    files=list(folder.glob('*.scs'))+[folder/'measure.json']
    inputs=[{'source':str(p.relative_to(ROOT)).replace('\\','/'),'name':p.name} for p in files]
    for name in [analyzer,'native_frames.py']:
        p=W/'scripts'/name;inputs.append({'source':str(p.relative_to(ROOT)).replace('\\','/'),'name':name})
    r=dict(schema_version=1,run_id=run,design_id='manual8_comparator_design',entry='test.scs',analyzer=analyzer,inputs=inputs,
           expected_stop_s=stop,summary_signals=signals,qualification_scope='Isolated comparator sizing measurement; no ADC baseline adoption',
           oa_parity='netlist only; user OA read-only',test_conditions=conditions or {'corner':'tt','vdd':.9,'temperature_c':27,'noise':False,'mismatch':False,'PEX':False},
           spectre_args=['+preset=cx','+mt=1','-preset_override'],resources={'threads':1,'simulation_rss_mib':1024,'simulation_virtual_mib':8192,
           'analysis_rss_mib':256,'analysis_virtual_mib':1024,'max_output_mib':512,'simulation_wall_seconds':900,'analysis_wall_seconds':600,'queue_timeout_seconds':600})
    write(W/'recipes'/(run+'.yaml'),json.dumps(r,indent=2)+'\n')

def main():
    source=ROOT/'verification/manual_adc/candidate_io_v1/dut.scs'
    text=source.read_text();body=re.search(r'subckt manual_cmp\b.*?ends manual_cmp',text,re.S).group(0)
    p=W/'baseline/comparator.scs'
    if p.exists() and p.read_text()!=body+'\n':raise ValueError('Frozen baseline differs')
    write(p,body+'\n')
    models=ROOT/'verification/manual_adc/joined_dc_v1/models.scs'
    write(W/'baseline/models_tt.scs',models.read_text())
    frame=ROOT/'scripts/manual_adc/reduce.py'
    write(W/'scripts/native_frames.py',frame.read_text())
    provenance={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [source,models,frame]}
    write(W/'baseline/provenance.json',json.dumps(provenance,indent=2)+'\n')
    folder=W/'testbenches/load_tt_v1';write(folder/'models.scs',models.read_text())
    d='simulator lang=spectre\ninclude "models.scs"\nVVDD (VDD 0) vsource dc=.9\n'
    signals=['VDD','VVDD:1'];windows=[]
    for tag,tr in [('F',.05),('S',.2)]:
        for side,t0 in [('P',5),('N',15)]:
            node=tag+side;src='V'+node
            d+='%s (%s 0) vsource type=pwl wave=[0 0 %gn 0 %gn .9 %gn .9 %gn 0]\n'%(src,node,t0,t0+tr,t0+5,t0+5+tr)
            signals += [node,src+':1']
            for k in range(8):d+='X%s%d (%s 0 Q%s%d VDD 0) DFQD1BWP12T30P140\n'%(node,k,node,node,k)
            windows += [{'source':src+':1','label':node+'_rise','start_s':t0*1e-9,'end_s':(t0+2)*1e-9,'dv':.9},
                        {'source':src+':1','label':node+'_fall','start_s':(t0+5)*1e-9,'end_s':(t0+7)*1e-9,'dv':-.9}]
        d+='XOR%s (%sP %sN VALID%s VDD 0) OR2D4BWP12T30P140\n'%(tag,tag,tag,tag)
    d+='simulatorOptions options reltol=1e-6 vabstol=1e-8 iabstol=1e-14 temp=27\nsaveOptions options save=selected currents=selected\ntran_test tran stop=25n maxstep=20p errpreset=conservative\nsave '+' '.join(signals)+'\n'
    write(folder/'test.scs',d);write(folder/'measure.json',json.dumps({'signals':signals,'windows':windows,'stop_s':25e-9},indent=2))
    recipe('cmpdesign-load-tt-v1',folder,signals,25e-9,'load_reduce.py')
    print('Frozen original comparator; generated load fixture, no simulation launched.')

if __name__=='__main__':main()
