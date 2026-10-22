"""Focused pre-run invariants, independent of expensive native simulations."""
from flow import ROOT, OUT, VERIFY, SINE, STATICS, candidate, read, dump, sha, schedule, blocks


def main():
    dut, _ = candidate(); frozen = (ROOT/'netlist/sar8_physical/dut.scs').read_text()
    keys=['kind','mode','honor_options','threads','frames','stop_ns','first','last',
          'samples','coherent_bin','warmup','half_span_lsb','refine','frequency_hz',
          'corner','VDD','temperature_C','transient_noise','mismatch',
          'strobe_period_ns','output_read_ns']
    evidence=[]
    for name in [SINE,*STATICS]:
        folder=OUT/'cases'/name; old=ROOT/'output/sar8_r4_performance/cases'/name
        c=read(folder/'context.json');a=read(old/'context.json')
        assert all(c[k]==a[k] for k in keys),name
        deck=folder/(name+'.scs');text=deck.read_text()
        assert text.count(dut)==1 and blocks(text)==blocks(dut)
        assert text.replace(dut,frozen)==(old/(name+'.scs')).read_text(),name
        assert sha(deck)==c['deck_sha256']
        new_models={i['path'].replace('\\','/').split('/')[-1]:i['sha256'] for i in c['includes']}
        old_models={i['path'].replace('\\','/').split('/')[-1]:i['sha256'] for i in a['includes']}
        assert new_models==old_models
        assert all(sha(i['path'])==i['sha256'] for i in c['includes'])
        evidence.append(dict(name=name,frames=c['frames'],deck_sha256=sha(deck),
                             fixture_identical_after_DUT_substitution=True,context_equal=True,models_equal=True))
    lanes=schedule(evidence,4)
    assert len(lanes[0])==1 and sum(j['frames'] for j in evidence)==3618
    setup=read(VERIFY/'setup.json')
    assert sha(ROOT/'verification/sar8_r4_performance/results.json')==setup['original_R4_results_sha256']
    dump(VERIFY/'preparation_checks.json',dict(pass_all=True,candidate_subcircuits=len(blocks(dut)),
        total_frames=3618,cases=evidence,lane_frames=[sum(j['frames'] for j in lane) for lane in lanes]))
    print('PASS all nine exact testbench substitutions, source hashes, contexts and scheduler')


if __name__=='__main__':main()
