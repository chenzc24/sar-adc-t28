"""Read-only snapshot of the observed long APS run for cross-engine checking.

This is explicitly NOT a completed simulation or an accepted FFT source.
No live simulator file is changed. Preserve the downloaded bytes verbatim.
"""
import re
from pathlib import Path
from common import OUT,dump,sha
from virtuoso_bridge import VirtuosoClient
from virtuoso_bridge.spectre.parsers import parse_spectre_psf_ascii

text=(OUT/'transient_runner.log').read_text(errors='replace')
matches=re.findall(r'(?m)^\[Command\].*? (/tmp/virtuoso_bridge_\S+/final_dynamic\.scs) .*?-raw (/tmp/virtuoso_bridge_\S+/final_dynamic\.raw) ',text)
assert len(matches)==1,matches
deck,raw=matches[0]
target=OUT/'diagnostics/aps_partial.tran'
assert not target.exists(),'Preserve prior snapshot'
target.parent.mkdir(parents=True,exist_ok=True)
c=VirtuosoClient.from_env(profile='t28_io')
# Filename follows the actual observed analysis naming in completed APS runs.
r=c.download_file(raw+'/tran.tran.tran',target,timeout=120)
assert not r.errors,r
p=parse_spectre_psf_ascii(target)
w={str(k).strip('"').replace('\\','').lower():v for k,v in p.data.items() if isinstance(v,list)}
keys=['time','topp','topn','valid','busy']+[f'dout<{b}>' for b in range(8)]
assert all(k in w for k in keys),(p.errors,list(w)[:20])
n=min(len(w[k]) for k in keys)
dump('diagnostics/aps_partial.json',{'diagnostic_only':True,'source_complete':False,
    'raw_sha256':sha(target),'remote_observed_deck':deck,'parser_errors':p.errors,
    'trimmed_to_complete_signal_rows':n,'waveform':{k:w[k][:n] for k in keys}})
print('PARTIAL_ONLY',n,'rows; last time s',w['time'][n-1],'; parser errors',p.errors)
