"""Check deck electrical invariance apart from authorized stimulus/observation."""
import ast,hashlib,json,re
from pathlib import Path
R=Path(__file__).resolve().parents[2]
O=R/'verification/manual_adc/bootstrap_fft_v1'
manifest=json.loads((O/'manifest.json').read_text())
checked=[]
for x in manifest['runs']:
    d=O/x['label'];source=R/x['config']['source_directory']
    old=(source/'test.scs').read_text();s=(d/'test.scs').read_text()
    a=s.split('ahdl_include "bootfft_observer.va"')[0].strip()
    a=re.sub(r'freq=[0-9.]+','freq=4501953.125',a)
    a=re.sub(r'tran_test tran[^\n]+',re.search(r'tran_test tran[^\n]+',old).group(0),a)
    a=re.sub(r'^save .*$',re.search(r'^save .*$',old,re.M).group(0),a,flags=re.M)
    assert a==old.strip(),x['label']
    for name,h in x['unchanged_circuit_sha256'].items():
        assert hashlib.sha256((d/name).read_bytes()).hexdigest()==h
        assert hashlib.sha256((source/name).read_bytes()).hexdigest()==h
    checked.append(x['run_id'])
for p in (R/'scripts/manual_adc').glob('bootstrap_fft_*.py'):
    ast.parse(p.read_text(encoding='utf-8'))
(O/'circuit_invariance.json').write_text(json.dumps(dict(pass_check=True,checked=checked,
    allowed_changes=['frequency','stop','save','strobe','read-only observer']),indent=2)+'\n')
print('Circuit invariance checked:',len(checked))
