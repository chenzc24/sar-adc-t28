"""Python2/3 streaming FFT/power reduction; bounded arrays of 1024 codes only."""
from __future__ import print_function
import argparse,cmath,json,math,os,re
from native_stream import samples

def spectrum(codes,k):
    n=len(codes);mean=sum(codes)/float(n);x=[complex(c-mean) for c in codes]
    # Radix2 FFT, independent of remote numpy availability.
    j=0
    for i in range(1,n):
        b=n>>1
        while j & b:j^=b;b>>=1
        j^=b
        if i<j:x[i],x[j]=x[j],x[i]
    size=2
    while size<=n:
        w=cmath.exp(-2j*math.pi/size)
        for start in range(0,n,size):
            f=1
            for q in range(size//2):
                a=x[start+q];z=f*x[start+q+size//2]
                x[start+q]=a+z;x[start+q+size//2]=a-z;f*=w
        size*=2
    power=[abs(z)**2*(1 if i in [0,n//2] else 2) for i,z in enumerate(x[:n//2+1])]
    sig=power[k];other=[v for i,v in enumerate(power) if i not in [0,k]]
    sndr=10*math.log10(sig/max(sum(other),1e-300))
    return dict(samples=n,bin=k,frequency_hz=1e7*k/n,sndr_db=sndr,
        sfdr_db=10*math.log10(sig/max(max(other),1e-300)),enob_bits=(sndr-1.76)/6.02,
        spectrum_dbc=[10*math.log10(max(v/sig,1e-30)) for v in power],
        method='Coherent rectangular FFT; DC removed; all nonfundamental bins in noise+distortion')

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--output-dir',required=True);a=p.parse_args()
    c=json.load(open(a.run_dir+'/inputs/context.json'));records=[];settings={};warnings=set()
    for line in open(a.run_dir+'/spectre.out'):
        m=re.search(r'R4MEAS,([^\r\n]+)',line)
        if m:records.append([float(x) for x in m.group(1).split(',')])
        warnings.update(re.findall(r'WARNING \(([^)]+)\)',line))
        for key in ['maxstep','reltol','abstol(V)','abstol(I)','method','errpreset']:
            m=re.match(r'\s*'+re.escape(key)+r' = (.+)',line)
            if m:settings[key]=m.group(1).strip()
    assert len(records)==c['frames']
    files=[a.run_dir+'/raw/'+n for n in os.listdir(a.run_dir+'/raw') if n.endswith('.tran.tran')];assert len(files)==1
    frames=[];prev=None;area=dict((s,0.) for s in ['vdd','ref_high','ref_low','clock']);points=0
    begin=59e-9+c['warmup']*1e-7;end=begin+1024e-7
    for t,v in samples(files[0]):
        points+=1
        frame=int(round((t-157e-9)/1e-7))
        if 0<=frame<c['frames'] and abs(t-(157+frame*100)*1e-9)<1e-13:
            frames.append(sum(1<<b for b in range(8) if v['d%d'%b]>.45))
        power=dict(vdd=-v['vdd!']*v['vvdd:p'],ref_high=-.9*v['vrefhigh:p'],
            ref_low=0.,clock=-v['sample']*v['vsample:p'])
        if prev:
            pt,pv=prev;l=max(pt,begin);h=min(t,end)
            if h>l:
                for key in area:
                    vl=pv[key]+(power[key]-pv[key])*(l-pt)/(t-pt)
                    vh=pv[key]+(power[key]-pv[key])*(h-pt)/(t-pt)
                    area[key]+=(vl+vh)*.5*(h-l)
        prev=(t,power)
    assert t>=c['stop_s']-1e-13 and len(frames)==c['frames']
    assert frames==[int(r[1]) for r in records]
    measured=records[c['warmup']:];assert len(measured)==1024
    bad=[int(r[0]) for r in measured if not r[7] or not 0<r[13]<60e-9]
    fft=spectrum(frames[c['warmup']:],461)
    watts=dict((key,value/(end-begin)) for key,value in area.items())
    result=dict(analysis_complete=True,context=c,native_decode_crosscheck=True,frames=records,
        codes=frames[c['warmup']:],invalid_steady_frames=bad,functional_pass=not bad,
        spectrum=fft,power_w=watts,power_core_plus_reference_w=watts['vdd']+watts['ref_high'],
        power_method='Trapezoidal integration of source power on10ps strobe grid; ideal input sources excluded; clock listed separately',
        power_qualification='Estimate pending native-point/grid-convergence check; not power signoff',
        effective_settings=settings,warning_codes=sorted(warnings),native_points=points,
        electrical_verdict='deferred_not_qualified',limitations=['No transient noise/mismatch/PEX','DC initialized low-first clock'])
    with open(a.output_dir+'/result.json','w') as f:json.dump(result,f,indent=2)
    print('DYNAMIC_COMPLETE',fft['sndr_db'],fft['enob_bits'])
if __name__=='__main__':main()
