"""Focused model baseline; actual ADCtoolbox metrics, reproducible config."""
from dataclasses import asdict,replace
from pathlib import Path
import json
import sys
import numpy as np
from adctoolbox import analyze_inl_from_ramp,analyze_spectrum
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from models.behavioral.sar_async import AsyncSAR


def main():
    adc=AsyncSAR();out=ROOT/"output/sar8_async_impl/model";out.mkdir(parents=True,exist_ok=True)
    ramp=-.9+(np.arange(2048)+.5)*1.8/2048
    results=[adc.convert(v) for v in ramp];codes=np.array([r.code for r in results])
    static=analyze_inl_from_ramp(codes,num_bits=8,endpoint="endpoints",exclude_endpoints=False,create_plot=False)
    n=4096;k=1843;vin=.9*10**(-1/20)*np.sin(2*np.pi*k*np.arange(n)/n)
    dynamic=[adc.convert(v) for v in vin];q=np.array([r.code for r in dynamic])
    metrics=analyze_spectrum((q+.5)*1.8/256-.9,fs=10e6,max_scale_range=(-.9,.9),win_type="rectangular",side_bin=0,create_plot=False)
    summary=dict(config=asdict(adc.cfg),seed=271828,static_samples=len(ramp),
        all_valid=all(r.valid and r.captures==8 for r in results+dynamic),
        missing_codes=len(static["missing_codes"]),dnl_min=float(static["dnl_min"]),dnl_max=float(static["dnl_max"]),
        inl_min=float(static["inl_min"]),inl_max=float(static["inl_max"]),
        coherent_samples=n,coherent_bin=k,input_frequency_hz=k*10e6/n,
        sndr_db=float(metrics["sndr_dbc"]),enob_bits=float(metrics["enob"]),
        completion_min_ns=min(r.completion_ns for r in dynamic),completion_max_ns=max(r.completion_ns for r in dynamic),
        scope="ideal_event_reference_not_native_circuit")
    rng=np.random.default_rng(271828)
    jitter=rng.normal(0,20e-12,n)
    noisy_vin=.9*10**(-1/20)*np.sin(2*np.pi*(k*10e6/n)*(np.arange(n)/10e6+jitter))
    lsb=1.8/256
    noisy=AsyncSAR(replace(adc.cfg,sample_noise_rms_v=.18*lsb,comparator_noise_rms_v=.18*lsb,
                           reference_noise_rms_v=.12*lsb),seed=271828)
    nr=[noisy.convert(v) for v in noisy_vin];nq=np.array([r.code for r in nr])
    nm=analyze_spectrum((nq+.5)*lsb-.9,fs=10e6,max_scale_range=(-.9,.9),win_type="rectangular",side_bin=0,create_plot=False)
    summary["allocated_noise_sensitivity"]=dict(seed=271828,sampling_noise_rms_lsb=.18,
        comparator_noise_rms_lsb=.18,reference_noise_rms_lsb=.12,sampling_jitter_rms_ps=20,
        sndr_db=float(nm["sndr_dbc"]),enob_bits=float(nm["enob"]),all_valid=all(r.valid for r in nr),
        scope="top_down_independent_noise_assumptions_not_transistor_noise")
    assert summary["all_valid"] and summary["missing_codes"]==0 and summary["enob_bits"]>7
    (out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    (out/"example_trace.json").write_text(json.dumps(adc.convert(.123).trace,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,indent=2))


if __name__=="__main__":main()
