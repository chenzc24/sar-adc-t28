"""Native six-frame checks plus matched frame-1 causal measurements and plots."""
import gc
import importlib.util
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from control import ROOT, OUT, VERIFY, SOURCE, NAMES, read, dump, sha

BASELINE = 'w2_ff_099_125_static'
FIG = ROOT / 'docs/figures/sar8_ff_counterfactual'


def bit_metrics(w, report, resistance):
    t = w['time'] * 1e9
    sup = report['vdd']
    def at(n, x):
        return float(np.interp(x, t, w[n]))
    def edges(n, up=True):
        v = w[n]; h = sup / 2
        ix = np.flatnonzero((v[:-1] < h) & (v[1:] >= h) if up else
                            (v[:-1] > h) & (v[1:] <= h))
        return t[ix] + (h-v[ix]) * (t[ix+1]-t[ix]) / (v[ix+1]-v[ix])
    cmp, wr, upd = [edges(n) for n in ['xdut.cmp_clk', 'xdut.xctrl.phi_w', 'xdut.phi_u']]
    assert len(cmp) == len(wr) == len(upd) == 8
    def word(prefix, x):
        return sum((at(prefix+str(b), x) > sup/2) * (1 << b) for b in range(8))
    def diff(x):
        return at('xdut.topp', x) - at('xdut.topn', x)
    rows = []
    for i, (ct, wt, ut) in enumerate(zip(cmp, wr, upd)):
        valid = (t >= ct) & (t <= wt) & (
            ((w['xdut.comp_p'] > .9*sup) & (w['xdut.comp_n'] < .1*sup)) |
            ((w['xdut.comp_n'] > .9*sup) & (w['xdut.comp_p'] < .1*sup)))
        assert valid.any()
        code = word('d', wt+.15)
        cp, cn = at('xdut.comp_p', wt), at('xdut.comp_n', wt)
        match = bool(((code >> (7-i)) & 1) == (cp > cn))
        assert match
        rows.append(dict(bit=7-i, compare_ns=float(ct), write_ns=float(wt), update_ns=float(ut),
            previous_update_to_compare_ns=float(ct-upd[i-1]) if i else None,
            reference_word=word('xdut.xref.q', ct-.01), top_before_mv=diff(ct-.01)*1000,
            residual_last100ps_change_uv=(diff(ct-.01)-diff(ct-.11))*1e6,
            reference_span_v=at('vrefp', ct-.01)-at('vrefn', ct-.01),
            code_after=code, comp_p_at_write=cp, comp_n_at_write=cn,
            resolved_90_10_before_write_ns=float(wt-t[valid][0]),
            compare_to_write_ns=float(wt-ct), write_matches_comparator=match))
    assert rows[-1]['code_after'] == report['frames'][1]['code']
    pp, nn = at('vrefp', 130), at('vrefn', 130)
    f = report['frames'][1]
    return dict(frame=1, input_v=-.81, reference_resistance_ohm=resistance,
        codes=[x['code'] for x in report['frames']], ideal_codes=[x['allowed_ideal_codes'] for x in report['frames']],
        code=f['code'], reference_p_130ns_v=pp, reference_n_130ns_v=nn, reference_span_130ns_v=pp-nn,
        positive_source_current_ua=(.9-pp)/resistance*1e6, negative_return_current_ua=nn/resistance*1e6,
        reference_p_drift_120_to_140ns_v=at('vrefp', 140)-at('vrefp', 120),
        reference_n_drift_120_to_140ns_v=at('vrefn', 140)-at('vrefn', 120),
        current_scope='Source resistor current, not a transistor leakage measurement',
        held_error_mv=f['held_error_v']*1000, preclose_error_mv=f['preclose_error_v']*1000,
        acquisition_ns=f['acquisition_ns'], sample_close_ns=float(edges('xdut.seq_sample', False)[0]),
        conversion_ns=f['conversion_ns'], last_reset_ns=f['last_reset_ns'],
        all_timing_pass=report['all_timing_pass'], all_idle_pass=report['all_idle_pass'],
        all_static_code_pass=report['static_code_pass'], CMI=report['CMI'],
        stress_failure_count=report['stress_failure_count'], effective_settings=report['effective_settings'],
        rows=rows)


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location('pvt_checks', ROOT/'scripts/sar8_pvt_mismatch/analyze.py')
    checks = importlib.util.module_from_spec(spec); spec.loader.exec_module(checks)
    checks.OUT = OUT; checks.VERIFY = VERIFY
    results, waves = {}, {}
    for name in [BASELINE]+NAMES:
        if name == BASELINE:
            source = SOURCE/'reduced/reduced.json.gz'
            assert sha(source) == read(SOURCE/'reduced_receipt.json')['compressed_sha256']
            cache = ROOT/'output/sar8_ff_timing'/(name+'.npz')
            old = read(ROOT/'verification/sar8_ff_timing'/(name+'.json'))
            assert sha(cache) == old['cache_sha256']
            w = dict(np.load(cache))
            report = read(ROOT/'verification/sar8_main_width'/(name+'.json'))
            resistance = 50
        else:
            report, raw = checks.analyze(name)
            time = np.array(raw['wave']['time'])
            mask = (time >= 100e-9) & (time < 200e-9)
            w = {k: np.array(v)[mask] for k, v in raw['wave'].items()}
            del raw; gc.collect()
            cache = OUT/(name+'.npz'); np.savez_compressed(cache, **w)
            resistance = read(OUT/name/'context.json')['reference_resistance_ohm']
        results[name] = bit_metrics(w, report, resistance)
        results[name].update(cache_sha256=sha(cache), native_psf_sha256=report['native_psf_sha256'])
        waves[name] = w
    base = results[BASELINE]
    assert all(r['rows'][5]['reference_word'] == 12 for r in results.values())
    for name in NAMES:
        assert results[name]['effective_settings'] == base['effective_settings']
        assert results[name]['all_timing_pass'] and results[name]['all_idle_pass'], 'Control timing confound'
        assert abs(results[name]['sample_close_ns']-base['sample_close_ns']) < .01
    dump(VERIFY/'comparison.json', dict(cases=results,
        scope='FF/0.99V/125C, 2um main, TT passive models, six static frames; no noise/mismatch/PEX',
        limitations=['No full-code or sine or PVT qualification', 'CMI/stress failures remain explicit',
                     'Lower source resistance is a diagnostic, not a physical reference buffer implementation',
                     'Branch-specific static current origin not measured']))
    colors = ['#b34238', '#007f83', '#6655a5']
    labels = ['Baseline: 50 ohm', 'Reference: 1 ohm', 'Wait: quiet C x2']
    fig, axs = plt.subplots(2, 1, figsize=(11, 6.5))
    for name, color, label in zip([BASELINE]+NAMES, colors, labels):
        w = waves[name]; t = w['time']*1e9; bit = results[name]['rows'][5]
        # Only show this bit's settling, no previous bit transition.
        style = '--' if name == 'ffhot_quiet2' else '-'
        axs[0].plot(t, (w['vrefp']-w['vrefn'])*1000, color=color, lw=1.5, ls=style, label=label)
        rel = t-bit['compare_ns']; use = (rel >= -1.5) & (rel <= -.01)
        axs[1].plot(rel[use], (w['xdut.topp'][use]-w['xdut.topn'][use])*1000,
                    color=color, lw=1.8, ls=style, label=f"{label}: {bit['top_before_mv']:+.3f} mV, code {results[name]['code']}")
    axs[0].axhline(900, color='black', ls='--', lw=.8, label='Ideal span: 900 mV')
    axs[0].set(xlim=(120, 140), ylim=(882, 902), ylabel='Reference span (mV)', xlabel='Time (ns)')
    axs[0].legend(loc='center left', ncol=2, fontsize=9)
    axs[0].set_title('Sampling phase: reference platform before conversion', fontsize=11)
    axs[1].axhline(0, color='black', ls='--', lw=.8)
    axs[1].axvline(0, color='gray', ls=':', lw=1)
    axs[1].set(xlim=(-1.5, .05), ylim=(-18, 7), ylabel='TOPP - TOPN (mV)', xlabel='Time relative to bit-2 compare edge (ns)')
    axs[1].legend(loc='center left', fontsize=9)
    axs[1].set_title('Bit 2, trial word 12: sign immediately before compare', fontsize=11)
    for ax in axs: ax.grid(alpha=.2)
    fig.suptitle('FF / 0.99 V / 125 C | native T28 ADC, Mmain 2 um | input -0.81 V\n'
                 'Fixed 10 MHz sample clock; ideal references + series R + 4 pF; no mismatch/noise/PEX', fontsize=11)
    fig.tight_layout(); fig.savefig(FIG/'causal_comparison.png', dpi=180); plt.close(fig)
    for name, r in results.items():
        print(name, r['codes'], 'span mV', r['reference_span_130ns_v']*1000,
              'bit2 mV', r['rows'][5]['top_before_mv'], 'conversion ns', r['conversion_ns'],
              'wait ns', r['rows'][5]['previous_update_to_compare_ns'])


if __name__ == '__main__':
    main()
