"""Selected native MOS operating-point outputs, not copied foundry model content."""
import re
from control import OUT,VERIFY,read,dump,sha

folder=OUT/'pair_ffhot_op';raw=folder/'native/test.raw/dc_info.info'
receipt=read(folder/'receipt.json')
assert sha(raw)==receipt['native_files']['test.raw/dc_info.info']
log=(folder/'native/spectre.out').read_text();status=(folder/'native/test.raw/logStatus').read_text()
assert 'spectre completes with 0 errors' in log and re.search(r'dc_oper\s+PASS',status)
text=raw.read_text();types=text.split('VALUE')[0]
structure=re.search(r'(?ms)^"tmibsimbulk" STRUCT\(\n(.*?)^\) PROP',types)[1]
keys=re.findall(r'(?m)^"([^"]+)" (?:FLOAT|INT)',structure)
rows={}
for mode in ['actual','ideal']:
    for side,dev in [('N','MN_LOW'),('P','MP_HIGH')]:
        name=f'X{mode}_{side}.{dev}'
        body=re.search(r'(?ms)^"'+re.escape(name)+r'" "tmibsimbulk" \(\n(.*?)^\)',text)[1]
        values=[float(x) for x in body.split()];assert len(keys)==len(values),(len(keys),len(values))
        op=dict(zip(keys,values))
        selected=['vgs','vds','vbs','vth','vdsat','ids','id','isub','igidl','igisl','ibd','ibs','igd','igs','igb','gm','gds','region']
        rows[name]={k:op[k] for k in selected if k in op}
dump(VERIFY/'operating_point.json',dict(psf_sha256=sha(raw),devices=rows,
     scope='Exact measured-hot bit7 pairs at DELTA0, native tmibsimbulk operating-point outputs; no ADC change'))
print(rows)
