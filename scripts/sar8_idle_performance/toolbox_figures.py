"""Offline ADCToolbox panel and explicitly time-referenced sine fit."""
from pathlib import Path
import sys
import json
import hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from adctoolbox.fundamentals import fit_sine_4param

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts/sar8_r4_performance'))
import toolbox_panel as panel

SOURCE = ROOT/'verification/sar8_idle_performance/results.json'
DEST = ROOT/'docs/figures/sar8_idle_performance'
VERIFY = ROOT/'verification/sar8_idle_performance'
FS, FIN, LSB = 10e6, 4501953.125, 1.8/256
AMP = .9*10**(-1/20)


def main():
    panel.main(SOURCE, DEST/'toolbox_panel.png', VERIFY/'toolbox_panel.json',
               source_key='candidate', label='Idle-tail reset SAR ADC',
               warning='No CMI warnings in this batch; not reliability sign-off.')
    r = json.loads(SOURCE.read_text(encoding='utf-8'))
    rows = r['candidate']['dynamic_frames']
    t = np.array([v['aperture_time_s'] for v in rows])
    frame = np.array([v['frame'] for v in rows])
    vin = np.array([v['aperture_source_v'] for v in rows])
    x = -.9+(np.array([v['code'] for v in rows])+.5)*LSB
    assert len(x) == 1024 and np.all(np.diff(frame) == 1)
    assert np.max(abs(vin-AMP*np.sin(2*np.pi*FIN*t))) < 1e-9
    assert np.max(abs(np.diff(t)-1/FS)) < 1e-12
    fit = fit_sine_4param(x, frequency_estimate=FIN/FS, max_iterations=0)
    fitted = np.asarray(fit['fitted_signal']).ravel()
    residual = np.asarray(fit['residuals']).ravel()
    assert np.max(abs(x-fitted-residual)) < 1e-12
    # Independently reconstruct the toolbox fit on a physical time axis.
    tn = t[0]+np.arange(1024)/FS
    w = 2*np.pi*FIN
    coeff = np.linalg.lstsq(np.column_stack([np.cos(w*tn), np.sin(w*tn), np.ones(1024)]), x, rcond=None)[0]
    def curve(tt):
        return coeff[0]*np.cos(w*tt)+coeff[1]*np.sin(w*tt)+coeff[2]
    assert np.max(abs(curve(tn)-fitted)) < 1e-10
    phase = np.arctan2(coeff[0], coeff[1])
    amplitude = np.hypot(coeff[0], coeff[1])
    raw = x-vin
    metrics = dict(samples=1024, source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        frequency_hz=FIN, fitted_amplitude_v=amplitude, input_amplitude_v=AMP,
        gain_difference_percent=(amplitude/AMP-1)*100, fitted_dc_mv=coeff[2]*1e3,
        phase_difference_deg=np.rad2deg(phase), equivalent_phase_shift_ns=phase/w*1e9,
        fitted_residual_rms_mv=np.sqrt(np.mean(residual**2))*1e3,
        fitted_residual_peak_mv=np.max(abs(residual))*1e3,
        clock_edge_difference_rms_mv=np.sqrt(np.mean(raw**2))*1e3,
        clock_edge_difference_peak_mv=np.max(abs(raw))*1e3,
        readout_after_internal_clock_edge_ns=float(np.mean((frame*100e-9+98e-9-t)*1e9)),
        timing_reference='Internal SAMPLE_INT falling 50% crossing, not physical aperture',
        phase_interpretation='Single-frequency equivalent phase shift; not a measured bootstrap delay',
        fit='Fixed known frequency; fit amplitude, phase and DC; no code correction')
    plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    fig, axs = plt.subplots(4,1,figsize=(13,11),layout='constrained')
    fig.suptitle('Idle-tail reset | Time-domain sine fit\nTT, 0.9 V, 27 C | 10 MS/s | 4.501953125 MHz | 1024 codes, -1 dBFS',fontsize=14)
    end = 12
    dense = np.linspace(t[0],t[end],4000)
    us = lambda tt: (tt-t[0])*1e6
    axs[0].plot(us(dense),AMP*np.sin(w*dense),color='.65',label='Applied differential input')
    axs[0].plot(us(dense),curve(dense),color='#167c87',ls='--',label='Output sine fit (all 1024 codes)')
    axs[0].scatter(us(t[:end+1]),x[:end+1],s=27,color='#c45442',label='Decoded codes at corresponding clock-edge times',zorder=4)
    axs[0].set(ylabel='Differential voltage (V)',title='(1) Sample-associated view: output codes moved back from readout time')
    read = frame*100e-9+98e-9
    axs[1].step(us(read[:end+1]),x[:end+1],where='post',color='#167c87',label='Readout sequence (held for display)')
    axs[1].scatter(us(t[:end+1]),vin[:end+1],color='.4',marker='x',label='Input at internal clock edge')
    axs[1].annotate('',xy=(us(read[0]),x[0]),xytext=(0,x[0]),arrowprops=dict(arrowstyle='<->',color='#c45442'))
    axs[1].set(ylabel='Decoded voltage (V)',title=f'(2) Readout view: {metrics["readout_after_internal_clock_edge_ns"]:.2f} ns after clock edge; not instantaneous bus waveform')
    axs[2].axhspan(-LSB*500,LSB*500,color='#167c87',alpha=.12,label='Ideal quantizer +/-0.5 LSB (reference)')
    axs[2].plot(us(t[:end+1]),residual[:end+1]*1e3,'o-',color='#167c87',label='Decoded output - fitted sine')
    axs[2].set(ylabel='Fit residual (mV)',title=f'(3) All-record residual RMS: {metrics["fitted_residual_rms_mv"]:.3f} mV; peak: {metrics["fitted_residual_peak_mv"]:.3f} mV')
    axs[3].plot(us(t[:end+1]),raw[:end+1]*1e3,'o-',color='#c45442',label='Decoded output - input at internal clock edge')
    axs[3].plot(us(t[:end+1]),(fitted[:end+1]-vin[:end+1])*1e3,'--',color='.3',label='Fitted phase / gain / DC contribution')
    axs[3].set(ylabel='Clock-edge difference (mV)',title='(4) Includes phase response; do not label as hold error')
    for ax in axs:
        ax.set_xlim(0,us(t[end]));ax.set_xlabel('Time from first measured internal clock edge (us)')
        ax.grid(alpha=.2);ax.legend(fontsize=8,loc='upper right');ax.axhline(0,color='.7',lw=.6)
    fig.supxlabel('Native T28 ADC; ideal external VDD / reference / SAMPLE | no transient noise, mismatch, PVT sweep or PEX\nInternal clock edge is a timing reference, not a calibrated sampling aperture. Fit is diagnostic, not calibration.',fontsize=9)
    fig.savefig(DEST/'time_fit.png',dpi=170);plt.close(fig)
    # Coherent phase-folding avoids implying a smooth time trace between near-Nyquist samples.
    phase_deg = np.rad2deg(np.mod(w*t,2*np.pi));order=np.argsort(phase_deg)
    pp=np.linspace(0,360,1500);rad=np.deg2rad(pp)
    fig,axs=plt.subplots(2,1,figsize=(11,7),layout='constrained',sharex=True)
    fig.suptitle('Idle-tail reset | 1024 samples folded into one input period\nTT, 0.9 V, 27 C | Fs 10 MHz, Fin 4.501953125 MHz | -1 dBFS',fontsize=13)
    axs[0].plot(pp,AMP*np.sin(rad),color='.5',label='Applied input sine')
    axs[0].plot(pp,amplitude*np.sin(rad+phase)+coeff[2],color='#167c87',ls='--',label='Output sine fit')
    axs[0].scatter(phase_deg,x,s=5,color='#c45442',alpha=.5,label='Decoded output (all samples)')
    axs[0].set_ylabel('Differential voltage (V)');axs[0].legend()
    axs[1].axhspan(-.5,.5,color='#167c87',alpha=.12,label='Ideal quantizer +/-0.5 LSB')
    axs[1].scatter(phase_deg[order],residual[order]/LSB,s=5,color='#167c87',label='Fit residual')
    axs[1].set(xlabel='Applied input phase at internal clock edge (degrees)',ylabel='Residual (LSB)',xlim=(0,360));axs[1].legend()
    for ax in axs:ax.grid(alpha=.2)
    fig.supxlabel('Phase-sorted data, NOT consecutive time samples | Ideal external sources | No noise / mismatch / PVT / PEX',fontsize=9)
    fig.savefig(DEST/'toolbox_phase_fold.png',dpi=170);plt.close(fig)
    (VERIFY/'toolbox_time_fit.json').write_text(json.dumps(panel.serial(metrics),indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(panel.serial(metrics),indent=2))


if __name__ == '__main__':
    main()
