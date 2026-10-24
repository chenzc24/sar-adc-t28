"""Aligned native-point waveforms; zoom clipping is explicit, no new simulation."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'output/sar8_bottom_undershoot'
FIG = ROOT / 'docs/figures/sar8_bottom_undershoot'
EVENTS = json.loads((ROOT / 'verification/sar8_bottom_undershoot/events.json').read_text())
COLORS = dict(bottom='#c54838', reference='#237c85', n='#2463a0', p='#914a9a')


def draw(phase):
    fig, axs = plt.subplots(4, 2, figsize=(11.6, 9.5), sharex='col')
    for col, (corner, temp) in enumerate([('m40', '-40'), ('125', '+125')]):
        key = f'symmetric25_ff_{corner}_{phase}'
        e = EVENTS[key]
        with np.load(DATA / (key + '.npz')) as f:
            w = {k: f[k] for k in f.files}
        t = w['time'] * 1e9
        a, b, peak = (e[k] for k in ['n_gate_start99_ns', 'p_gate_start99_ns', 'bottom_min_ns'])
        lo, hi = a - .035, e['bottom_zero_ns'] + .105
        bot = e['bottom'].split('.')[-1].upper()
        gn, gp = (e[k].split('.')[-1].upper() for k in ['gate_n', 'gate_p'])
        cmd = 'RST7' if phase == 'idle' else 'PHI_U'
        axs[0, col].set_title(f'FF {temp} C | {bot} | Vin,diff = {e["input_diff_v"]*1000:.3f} mV\n'
                              f'{cmd} at {e["command_rise_ns"]:.3f} ns', fontsize=10)
        axs[0, col].plot(t, w[e['bottom']], color=COLORS['bottom'], label=bot)
        axs[0, col].axhline(.9, color='0.5', ls='--', lw=.8, label='Nominal high reference')
        axs[0, col].axhline(0, color='0.5', ls=':', lw=.8)
        axs[0, col].set_ylim(-.10, 1.02)
        axs[0, col].set_ylabel('Bottom (V)')
        ax = axs[1, col]
        old = f'null_ff_{corner}_{phase}'
        with np.load(DATA / (old + '.npz')) as f:
            ax.plot(f['time'] * 1e9, f[e['bottom']] * 1000, color='0.45', ls='--', lw=1.1, label='Without holds')
        ax.plot(t, w[e['bottom']] * 1000, color=COLORS['bottom'], label=f'{bot}, symmetric holds')
        ax.plot(t, w['vrefn'] * 1000, color=COLORS['reference'], label='Actual VREFN')
        ax.axhline(0, color='0.5', lw=.8)
        ax.scatter([peak], [e['bottom_min_mv']], s=18, color=COLORS['bottom'], zorder=6)
        ax.annotate(f'{e["bottom_min_mv"]:.2f} mV\n{peak:.3f} ns',
                    xy=(peak, e['bottom_min_mv']), xytext=(peak+.033, -38),
                    fontsize=9, color=COLORS['bottom'],
                    arrowprops=dict(arrowstyle='->', color=COLORS['bottom'], lw=.8))
        ax.set_ylim(-66, 12)
        ax.set_ylabel('Negative zoom (mV)')
        axs[2, col].plot(t, w['vrefp'], color=COLORS['reference'], label='Actual VREFP')
        axs[2, col].axhline(.9, color='0.5', ls='--', lw=.8, label='Nominal 0.9 V')
        axs[2, col].set_ylim(.87, .92)
        axs[2, col].set_ylabel('High reference (V)')
        axs[3, col].plot(t, w[e['gate_n']], color=COLORS['n'], label=f'{gn}: MN_LOW gate')
        axs[3, col].plot(t, w[e['gate_p']], color=COLORS['p'], label=f'{gp}: MP_HIGH gate')
        axs[3, col].axhline(.99, color='0.5', ls=':', lw=.7)
        axs[3, col].set_ylim(-.07, 1.07)
        axs[3, col].set_ylabel('Gate voltage (V)')
        axs[3, col].set_xlabel('Absolute simulation time (ns)')
        for row in range(4):
            ax = axs[row, col]
            ax.axvspan(a, b, color=COLORS['n'], alpha=.07)
            ax.axvspan(b, peak, color=COLORS['p'], alpha=.12)
            ax.axvline(a, color=COLORS['n'], ls=':', lw=.8)
            ax.axvline(b, color=COLORS['p'], ls=':', lw=.8)
            ax.axvline(peak, color=COLORS['bottom'], ls=':', lw=.8)
            ax.set_xlim(lo, hi)
            ax.grid(alpha=.17)
            ax.ticklabel_format(useOffset=False, axis='x')
            ax.legend(loc='upper left' if row in [0, 1, 2] else 'upper right', fontsize=8, framealpha=.85)
        axs[0, col].text((a+b)/2, .55, 'A', ha='center', color=COLORS['n'], fontsize=12)
        axs[0, col].text((b+peak)/2, .55, 'B', ha='center', color=COLORS['p'], fontsize=12)
    title = 'Idle reset: BN7 changes from VREFN to VREFP' if phase == 'idle' else 'First MSB update: BP7 changes from VREFN to VREFP'
    fig.suptitle(title, fontsize=14, y=.986)
    fig.text(.5, .951, 'Native T28 ADC | core 0.99 V | reference 50 ohm / 4 pF | Lref 90 nm | ideal idle gate holds', ha='center', fontsize=9)
    fig.text(.5, .018, 'A: low-N gate falling. B: high-P gate begins falling. Markers = 99% rail, not MOS thresholds.\n'
             'Row 2 clips the later positive transition; row 1 shows its full range. Saved native points; no new simulation.', ha='center', fontsize=9)
    fig.subplots_adjust(top=.875, bottom=.105, left=.085, right=.98, hspace=.14, wspace=.22)
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / f'{phase}_handoff.png', dpi=180)
    plt.close(fig)


if __name__ == '__main__':
    draw('idle')
    draw('conversion')
