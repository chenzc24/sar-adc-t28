"""Python2/3: reuse validated FFT reducer and compare frozen no-noise result."""
from __future__ import print_function
import argparse,json,os,re
import dynamic_reduce

def compare(result,baseline):
    a=baseline['context'];b=result['context']
    for key in ['dut_sha256','frames','warmup','samples','bin','frequency_hz','vdd','temperature_c','reference_v','solver_profile']:
        assert a[key]==b[key],key
    assert not a['noise'] and b['noise']
    assert result['effective_settings']==baseline['effective_settings']
    assert len(result['codes'])==len(baseline['codes'])==1024
    differences=[x-y for x,y in zip(result['codes'],baseline['codes'])]
    rows=result['frames'];old=baseline['frames']
    invalid=[int(r[0]) for r in rows if r[2:6]!=[8,8,8,16] or r[1]!=r[6] or r[7]!=1 or not 0<r[13]<60e-9]
    return dict(baseline_run_id=a['run_id'],noisy_run_id=b['run_id'],
        noise_minus_baseline=dict((k,result['spectrum'][k]-baseline['spectrum'][k]) for k in ['sndr_db','sfdr_db','enob_bits']),
        baseline_metrics=dict((k,baseline['spectrum'][k]) for k in ['sndr_db','sfdr_db','enob_bits']),
        noisy_metrics=dict((k,result['spectrum'][k]) for k in ['sndr_db','sfdr_db','enob_bits']),
        changed_codes=sum(d!=0 for d in differences),max_abs_code_difference=max(map(abs,differences)),
        code_difference_is_not_error_verdict=True,invalid_all_frames=invalid,
        max_conversion_ns=max(r[13] for r in rows)*1e9,
        baseline_max_conversion_ns=max(r[13] for r in old)*1e9,
        max_close_edge_difference_ps=max(abs(x[9]-y[9]) for x,y in zip(rows,old))*1e12,
        core_plus_reference_power_difference_w=result['power_core_plus_reference_w']-baseline['power_core_plus_reference_w'],
        power_is_grid_estimate=True,bandwidth_convergence='not_established',seed_count=1)

def svg(result,baseline,path):
    parts=['<svg xmlns="http://www.w3.org/2000/svg" width="960" height="480" viewBox="0 0 960 480">',
        '<rect width="960" height="480" fill="white"/>',
        '<text x="70" y="30" font-family="sans-serif" font-size="20">B TT 1024: no-noise vs transient noise (2 GHz, 10 kHz, seed101)</text>']
    for db in [0,-20,-40,-60,-80,-100,-120]:
        y=55-db*3
        parts.append('<path d="M70 %s H920" stroke="#ddd"/><text x="22" y="%s" font-family="sans-serif" font-size="13">%s</text>'%(y,y+5,db))
    for f in range(6):
        x=70+f*170
        parts.append('<text x="%s" y="440" font-family="sans-serif" font-size="13">%s</text>'%(x,f))
    for d,color,label,tx in [(baseline,'#777','No noise',70),(result,'#1268cc','Transient noise',240)]:
        pts=' '.join('%.2f,%.2f'%(70+i*850./512,55-min(0,max(-120,v))*3) for i,v in enumerate(d['spectrum']['spectrum_dbc']) if i>0)
        parts.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="1"/><text x="%s" y="465" font-family="sans-serif" font-size="14" fill="%s">%s</text>'%(pts,color,tx,color,label))
    parts.append('<text x="800" y="465" font-family="sans-serif" font-size="14">Frequency (MHz)</text></svg>')
    with open(path,'w') as f:f.write('\n'.join(parts))

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--output-dir',required=True);a=p.parse_args()
    dynamic_reduce.main()
    path=a.output_dir+'/result.json';r=json.load(open(path));base=json.load(open(a.run_dir+'/inputs/baseline_result.json'))
    settings={}
    for line in open(a.run_dir+'/spectre.out'):
        m=re.match(r'\s*(noisefmax|noisefmin|noiseseed|noisescale)\s*=\s*(.+)',line)
        if m:settings[m.group(1)]=m.group(2).strip()
    assert settings.get('noisefmax')=='2 GHz' and settings.get('noisefmin')=='10 kHz' and settings.get('noiseseed')=='101',settings
    r['native_noise_settings']=settings
    r['limitations']=['Single noise seed; bandwidth convergence not established','Below10kHz source PSD is flattened; no long-term flicker claim','No mismatch/PEX/external source noise or external clock jitter','Original noise_worst section retained','Power estimate on10ps grid; no convergence signoff','DC initialized low-first clock']
    c=compare(r,base);r['functional_pass']=r['functional_pass'] and not c['invalid_all_frames']
    r['noise_baseline_comparison']=c
    with open(path,'w') as f:json.dump(r,f,indent=2)
    with open(a.output_dir+'/comparison.json','w') as f:json.dump(c,f,indent=2)
    svg(r,base,a.output_dir+'/spectrum_comparison.svg')
    print('NOISY_FFT_COMPARISON_COMPLETE',r['functional_pass'],c['noise_minus_baseline'])

if __name__=='__main__':main()
