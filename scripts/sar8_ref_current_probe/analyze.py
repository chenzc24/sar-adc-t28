"""Current sign/KCL validation and baseline-only diagnostic analysis."""
import json,re,sys
import numpy as np
from probe import ROOT,OUT,VERIFY,read,dump,sha

def load(name):
 d=OUT/name/'reduced_v2';receipt=read(d/'receipt.json');meta=read(d/'wave.meta.json')
 for fn in ['wave.columns','wave.meta.json','trace.txt','spectre.out','logStatus','finished.json']:
  assert sha(d/fn)==receipt['files'][fn]['sha256']
 cols=(d/'wave.columns').read_text().splitlines()
 assert (d/'wave.bin').stat().st_size==meta['points']*meta['columns']*8
 m=np.memmap(d/'wave.bin',mode='r',dtype='<f8',shape=(meta['points'],meta['columns']))
 w={n:m[:,i] for i,n in enumerate(cols)};t=w['time']*1e9
 assert meta['PSF_END'] and np.all(np.diff(t)>0)
 assert read(d/'finished.json')['exit_code']==0
 assert 'spectre completes with 0 errors' in (d/'spectre.out').read_text()
 assert re.search(r'tran_perf\s+PASS',(d/'logStatus').read_text())
 expected=read(OUT/name/'manifest.json')['currents']
 trace=(d/'trace.txt').read_text()
 assert all(('"'+x+'" "I"') in trace for x in expected)
 return d,m,w,t

def checks(w):
 peak=lambda x:float(np.max(np.abs(x)))
 results={}
 for side in ['p','n']:
  for bit in range(8):
   prefix='xdut.xcdac.xs%s%d.'%(side,bit)
   currents=[w[prefix+dev+':1'] for dev in ['mn_low','mp_high']]
   currents.append(w['xdut.xcdac.cmom%s%d:2'%(side,bit)])
   residual=sum(currents);scale=max(peak(x) for x in currents)
   results['bottom_b%s%d'%(side,bit)]=dict(residual_a=peak(residual),peak_branch_a=scale)
   for dev in ['mn_low','mp_high']:
    terminals=[w[prefix+dev+':'+str(p)] for p in range(1,5)]
    results['MOS_'+prefix+dev]=dict(residual_a=peak(sum(terminals)),peak_branch_a=max(peak(x) for x in terminals))
 for bit,gate,side,dev in [(7,'gpn','p','mn_low'),(7,'gpp','p','mp_high'),(4,'gnn','n','mn_low'),(4,'gnp','n','mp_high'),(3,'gpn','p','mn_low'),(3,'gpp','p','mp_high')]:
  ig=w['xdut.xcdac.xs%s%d.%s:2'%(side,bit,dev)]
  ir=w['xdut.xref.xdrv%d.r%s1_5__dmy0:2'%(bit,gate)]
  results['gate_'+gate+str(bit)]=dict(residual_a=peak(ig+ir),peak_branch_a=max(peak(ig),peak(ir)))
 for rail,source in [('p',.9),('n',0.)]:
  ir=w['rref'+rail+':1'];expected=(source-w['vref'+rail])/50
  results['reference_resistor_'+rail]=dict(residual_a=peak(ir-expected),peak_branch_a=peak(ir))
 return results

def smoke():
 d,m,w,t=load('smoke_cold');kcl=checks(w)
 # A current direction/multiplicity error would fail node balance and Ohm's law.
 passed=all(x['residual_a']<max(1e-10,1e-4*x['peak_branch_a']) for x in kcl.values())
 out=dict(passed=passed,points=len(t),stop_ns=float(t[-1]),terminal_currents=228,
  kcl=kcl,max_current_a=max(float(np.max(np.abs(w[n]))) for n in w if ':' in n),
  sign='Positive current enters the saved component terminal; wrapper ports D,G,S,B = 1,2,3,4.',
  scaling='Saved wrapper terminal current already represents the complete parallel multiplicity; do not multiply again.',
  limitation='Short initialization probe; repeat KCL checks in full transient event windows.')
 dump(VERIFY/'smoke_validation.json',out);print(json.dumps(out,indent=2));assert passed

if __name__=='__main__':
 if sys.argv[1]=='smoke':smoke()
