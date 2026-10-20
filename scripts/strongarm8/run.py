"""Read-only native OA provenance and unchanged-DUT comparator experiments."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from concurrent.futures import as_completed
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/strongarm8_baseline"
os.environ.setdefault("VB_DISABLE_CONTROL_MASTER", "1")
sys.path.insert(0, str(ROOT / "scripts/characterization"))
from run_strongarm_t28 import assert_export
from verify_strongarm_t28 import dut_block


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def dump(name, value):
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, default=str) + "\n", encoding="utf-8")


def config():
    return yaml.safe_load((ROOT / "config/strongarm8_baseline.yaml").read_text())


def once(text, old, new):
    assert text.count(old) == 1, (old, text.count(old))
    return text.replace(old, new, 1)


def source():
    p = json.loads((OUT / "provenance.json").read_text())
    s = Path(p["exports"][config()["testbench"]]["path"]).read_text()
    assert sha(s) == p["exports"][config()["testbench"]]["sha256"]
    return s


def base(vd, *, sup=.9, cm=None, load=5e-15, corner="tt", temp=27):
    original = source()
    cm = sup / 2 if cm is None else cm
    s = once(original, "parameters vinn vinp", f"parameters vinn={cm-vd/2:.14g} vinp={cm+vd/2:.14g}")
    s = once(s, "dc=900m type=dc", f"dc={sup:.14g} type=dc")
    s = once(s, "val1=900m period=5n", f"val1={sup:.14g} period=5n")
    s = once(s, "temp=27 tnom=27", f"temp={temp} tnom=27")
    s = once(s, "section=ttmacro_mos_moscap", f"section={corner}macro_mos_moscap")
    s = s.replace("capacitor c=5f", f"capacitor c={load:.14g}")
    s = s.replace("reltol=1e-4", "reltol=1e-5").replace("vabstol=1e-6", "vabstol=1e-8")
    s = s.replace("iabstol=1e-12", "iabstol=1e-14").replace("save=allpub", "save=selected")
    s = re.sub(r"(?m)^\w+ info .*\n", "", s)
    assert dut_block(s) == dut_block(original)
    return s


def case(name, s, **meta):
    assert dut_block(s) == dut_block(source())
    p = OUT / "decks" / f"{name}.scs"
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists() and p.read_text() != s:
        raise RuntimeError(f"Refuse to overwrite existing experiment {name}")
    p.write_text(s, encoding="utf-8")
    dump(f"cases/{name}.json", {"name": name, "deck_sha256": sha(s),
         "dut_sha256": sha(dut_block(s)), **meta})
    return p


def simulate(paths, *, workers=3, timeout=3600, includes=()):
    from virtuoso_bridge.spectre import SpectreSimulator
    from virtuoso_bridge.spectre.runner import spectre_mode_args
    sim = SpectreSimulator.from_env(profile="t28_io", work_dir=OUT / "spectre",
        timeout=timeout, spectre_args=[*spectre_mode_args("aps"), "+lqtimeout", "5"])
    pending = []
    for p in paths:
        f = OUT / "results" / f"{p.stem}.json"
        if f.exists() and json.loads(f.read_text()).get("ok"):
            assert json.loads(f.read_text())["deck_sha256"] == sha(p.read_text())
        else:
            pending.append(p)
    with sim.parallel_pool(max_workers=workers) as pool:
        submitted = {pool.submit(p, {"include_files":list(includes)}): p for p in pending}
        for future in as_completed(submitted):
            p = submitted[future]
            try:
                r = future.result()
                row = {"name": p.stem, "ok": r.ok, "errors": r.errors,
                       "warnings": r.warnings, "metadata": r.metadata,
                       "deck_sha256": sha(p.read_text()), "mode": "aps"}
                dump(f"results/{p.stem}.json", row)
                if r.ok:
                    # Only actual transient vectors; omit model/parameter tables.
                    wanted = {k: v for k, v in r.data.items() if k != "units" and isinstance(v, (list, tuple))}
                    dump(f"waves/{p.stem}.json", {str(k).replace("\\", "").lower(): v for k, v in wanted.items()})
                print("DONE", p.stem, r.ok, r.errors[:2], flush=True)
            except Exception as exc:
                dump(f"results/{p.stem}_exception.json", {"name": p.stem, "error": repr(exc)})
                print("EXCEPTION", p.stem, repr(exc), flush=True)


def deterministic(smoke=False):
    cfg = config()
    over = cfg["targets"]["decision_overdrive_v"]
    conditions = [("nom", "tt", .9, 27, .45, 5e-15, over),
                  ("ss_cold", "ss", .81, -40, .405, 20e-15, over)]
    if not smoke:
        conditions = []
        for co in cfg["pvt"]["corners"]:
            for sup in cfg["pvt"]["supplies_v"]:
                for temp in cfg["pvt"]["temperatures_c"]:
                    conditions.append((f"pvt_{co}_{round(sup*1000)}_{temp}",co,sup,temp,sup/2,20e-15,over))
        for cm in cfg["common_mode_screen_v"]:
            conditions.append((f"cm_{round(cm*1000)}","tt",.9,27,cm,5e-15,over))
        for mult in (.025, .1, .25, .5, 1, 2):
            conditions.append((f"ov_{mult:g}","tt",.9,27,.45,5e-15,mult*cfg["span_v"]/256))
    paths = []
    for name, co, sup, temp, cm, load, vd in conditions:
        for sign in (1,-1):
            s = base(sign*vd, sup=sup, cm=cm, load=load, corner=co, temp=temp)
            s += "\ntran tran stop=17n maxstep=2p errpreset=conservative\n"
            s += "save OUTP OUTN CLK VINP VINN XCMP.X XCMP.Y XCMP.TAIL VVDD:p VCLK:p\n"
            paths.append(case(f"det_{name}_{'p' if sign>0 else 'n'}",s,
                category="deterministic",corner=co,supply_v=sup,temperature_c=temp,
                common_mode_v=cm,load_f=load,differential_v=sign*vd))
    simulate(paths)


def noise(smoke=False, bandwidth=False):
    cfg = config()["noise"]
    paths = []
    cycles = 12 if smoke else int(cfg["cycles"])
    inputs = [0.0] if smoke else ([-.0005,0,.0005] if bandwidth else cfg["inputs_v"])
    seeds = cfg["seeds"] if not bandwidth else cfg["seeds"][:1]
    fmax = 30e9 if bandwidth else cfg["fmax_hz"]
    for vd in inputs:
        for seed in seeds:
            s = base(vd)
            stop = 5e-9*cycles+2e-9
            s += (f"\ntran tran stop={stop:.14g} maxstep=5p errpreset=conservative "
                  f"noisefmax={fmax:.14g} noisefmin={cfg['fmin_hz']:.14g} noiseseed={seed}")
            if not smoke:
                s += " strobeperiod=5n strobedelay=1.51n strobeoutput=strobeonly"
            s += "\nsave OUTP OUTN CLK VINP VINN\n"
            if smoke:
                s += "save XCMP.X XCMP.Y\n"
            name=f"noise_{'pilot' if smoke else 'cdf_phase'}_{round(vd*1e6)}u_{seed}_{round(fmax/1e9)}G"
            paths.append(case(name,s,category="noise",differential_v=vd,seed=seed,
                              cycles=cycles,fmin_hz=cfg["fmin_hz"],fmax_hz=fmax,
                              strobe_only=not smoke))
    simulate(paths,workers=2)


def mismatch(smoke=False):
    cfg = config()["mismatch"]
    count = round(2*cfg["fine_range_v"]/cfg["step_v"])
    values = sorted(set([round(-cfg["fine_range_v"]+i*cfg["step_v"],9) for i in range(count+1)]+
                        cfg["guard_inputs_v"]+[-.0017578125,.0017578125]))
    seq = values + list(reversed(values))
    draws = 4 if smoke else int(cfg["draws"])
    s = base(0)
    for name, net, factor in (("VIPP","VINP",1),("VNN_SRC","VINN",-1)):
        points = [(0,.45+factor*seq[0]/2)]
        for k, vd in enumerate(seq[1:],1):
            change=k*5e-9+2.8e-9
            points += [(change,.45+factor*seq[k-1]/2),(change+100e-12,.45+factor*vd/2)]
        pwl=" ".join(f"{t:.14g} {v:.14g}" for t,v in points)
        s=once(s,f"{name} ({net} 0) vsource dc={'vinp' if factor>0 else 'vinn'} type=dc",
               f"{name} ({net} 0) vsource type=pwl wave=[ {pwl} ]")
    s=once(s,"section=ttmacro_mos_moscap",f"section={cfg['section']}")
    s += (f"\nmc montecarlo numruns={draws} seed={cfg['seed']} variations=mismatch "
          "sampling=standard donominal=no savemismatchparams=yes "
          'mismatchparamfile="mismatch_params.txt" savefamilyplots=yes savedatainseparatedir=yes {\n'
          f"tran tran stop={len(seq)*5e-9+2e-9:.14g} maxstep=5p errpreset=conservative "
          "strobeperiod=5n strobedelay=1.51n strobeoutput=strobeonly\n}\nsave OUTP OUTN CLK\n")
    p=case(f"mc_offset_{draws}_phase",s,category="mismatch",draws=draws,seed=cfg["seed"],
           section=cfg["section"],input_sequence_v=seq,threshold_resolution_v=cfg["step_v"])
    simulate([p],workers=1)


def mismatch_binary(smoke=False):
    cfg=config()["mismatch"];draws=4 if smoke else cfg["draws"]
    s=base(0)
    for name,node,param in (("VIPP","VINP","vinp"),("VNN_SRC","VINN","vinn")):
        s=once(s,f"{name} ({node} 0) vsource dc={param} type=dc", "")
    s=once(s,"section=ttmacro_mos_moscap",f"section={cfg['section']}")
    va=ROOT/"scripts/strongarm8/offset_search.va"
    s+='\nXSEARCH (VINP VINN OUTP OUTN SEARCH_LO SEARCH_HI SEARCH_DONE SEARCH_BAD 0) strongarm8_offset_search\n'
    s+=(f"mc montecarlo numruns={draws} seed={cfg['seed']} variations=mismatch sampling=standard "
        'donominal=no savemismatchparams=yes mismatchparamfile="mismatch_params.txt" '
        'savefamilyplots=yes savedatainseparatedir=yes {\n'
        'tran tran stop=54n maxstep=5p errpreset=conservative '
        'strobeperiod=5n strobedelay=3n strobeoutput=strobeonly\n}\n'
        'save OUTP OUTN CLK VINP VINN SEARCH_LO SEARCH_HI SEARCH_DONE SEARCH_BAD\n'
        'ahdl_include "offset_search.va"\n')
    p=case(f"mc_binary_{draws}",s,category="mismatch_binary",draws=draws,seed=cfg["seed"],
        section=cfg["section"],threshold_resolution_v=.00025,stimulus_sha256=sha(va.read_text()),
        scope="testbench binary-search input; native unchanged comparator; physical noise disabled")
    simulate([p],workers=1,includes=[va])


def held():
    cfg = config()
    paths=[]
    for vd in (-cfg["targets"]["decision_overdrive_v"],0,cfg["targets"]["decision_overdrive_v"]):
        s=base(vd)
        for name,node,param in (("VIPP","VINP","vinp"),("VNN_SRC","VINN","vinn")):
            s=once(s,f"{name} ({node} 0) vsource dc={param} type=dc",
                f"{name} ({node}_BIAS 0) vsource dc={param} type=dc\n"
                f"R{node} ({node}_BIAS {node}) resistor r=1G\n"
                f"C{node} ({node} 0) capacitor c={cfg['kickback']['side_capacitance_f']:.14g}")
        s+="\ntran tran stop=17n maxstep=2p errpreset=conservative\nsave OUTP OUTN CLK VINP VINN VVDD:p\n"
        paths.append(case(f"held_{round(vd*1e6)}u",s,category="held",differential_v=vd,
                          capacitance_f=cfg["kickback"]["side_capacitance_f"]))
    simulate(paths)


def integrated():
    cfg = config()
    provenance = json.loads((OUT / "provenance.json").read_text())
    original = Path(provenance["exports"][cfg["cdac_testbench"]]["path"]).read_text()
    assert sha(original) == provenance["exports"][cfg["cdac_testbench"]]["sha256"]
    paths=[]
    for vd in (-cfg["targets"]["decision_overdrive_v"],0,cfg["targets"]["decision_overdrive_v"]):
        for enabled in (False, True):
            values={"SUP":.9,"RREF":50,"CDECAP":4e-12,"CKB":.05e-15,"DEAD_TIME":100e-12,
                    "OPEN_LOOP":1,"FIXED_CODE":128,"STIM_MODE":0,"VDIFF":vd,"FIN":4.5e6,
                    "MULT_R":1,"MULT_S":1,"MULT_D":1}
            m=re.search(r"(?m)^parameters ((?:[^\n]*\\\n)*[^\n]*)\n",original)
            names=m[1].replace("\\\n"," ").split()
            assert set(names) <= set(values),(names,values)
            s=original[:m.start()]+"parameters "+" ".join(f"{n}={values[n]:.14g}" for n in names)+"\n"+original[m.end():]
            s=once(s,"XCOMP (CMP_CLK COMP_N COMP_P", "XCOMP (CMP_TEST COMP_N COMP_P")
            s=s.replace("save=allpub","save=selected").replace("reltol=1e-4","reltol=1e-5")
            s=s.replace("vabstol=1e-6","vabstol=1e-8").replace("iabstol=1e-12","iabstol=1e-14")
            s=re.sub(r"(?m)^\w+ info .*\n","",s)
            s+=(f"\nVCMP_TEST (CMP_TEST 0) vsource type=pulse val0=0 val1={.9 if enabled else 0} "
                "period=5n delay=46n rise=20p fall=20p width=1.53n\n"
                "tran tran stop=84n maxstep=5p errpreset=conservative\n"
                "save TOPP TOPN PHI DAC_SAMPLE BASE CMP_TEST COMP_P COMP_N VCM VREFP VREFN VVDD:p\n")
            s+="save "+" ".join(f"XCDAC.B{side}{b}" for side in "PN" for b in range(9))+"\n"
            p=case(f"cdac_{round(vd*1e6)}u_{'on' if enabled else 'off'}",s,category="cdac",
                differential_v=vd,comparator_enabled=enabled,load_f=5e-15,
                scope="native present CDAC/Bootstrap fixed code128; eight comparator pulses; stop before reference reset")
            paths.append(p)
    simulate(paths,workers=2)


def precision():
    vd=config()["targets"]["decision_overdrive_v"]
    s=base(vd).replace("reltol=1e-5","reltol=2e-6")
    s+="\ntran tran stop=17n maxstep=500f errpreset=conservative\nsave OUTP OUTN CLK VINP VINN XCMP.X XCMP.Y XCMP.TAIL VVDD:p VCLK:p\n"
    simulate([case("det_precision_p",s,category="deterministic",corner="tt",supply_v=.9,
        temperature_c=27,common_mode_v=.45,load_f=5e-15,differential_v=vd)])
    s=base(vd,sup=.81,cm=.405,load=5e-15,corner="ss",temp=-40).replace("reltol=1e-5","reltol=2e-6")
    s+="\ntran tran stop=17n maxstep=500f errpreset=conservative\nsave OUTP OUTN CLK VINP VINN XCMP.X XCMP.Y XCMP.TAIL VVDD:p VCLK:p\n"
    simulate([case("det_precision_cold5f_p",s,category="deterministic",corner="ss",supply_v=.81,
        temperature_c=-40,common_mode_v=.405,load_f=5e-15,differential_v=vd)])


def cold_common_mode():
    vd=config()["targets"]["decision_overdrive_v"];paths=[]
    for cm in (.405,.45,.50):
        for load in (5e-15,20e-15):
            for sign in (-1,1):
                s=base(sign*vd,sup=.81,cm=cm,load=load,corner="ss",temp=-40)
                s+="\ntran tran stop=17n maxstep=2p errpreset=conservative\nsave OUTP OUTN CLK VINP VINN XCMP.X XCMP.Y XCMP.TAIL VVDD:p VCLK:p\n"
                paths.append(case(f"det_coldcm_{round(cm*1000)}_{round(load*1e15)}f_{'p' if sign>0 else 'n'}",s,
                    category="deterministic",corner="ss",supply_v=.81,temperature_c=-40,common_mode_v=cm,
                    load_f=load,differential_v=sign*vd,scope="common-mode and load sensitivity, not a changed ADC VCM"))
    simulate(paths,workers=2)


def export():
    from virtuoso_bridge import VirtuosoClient
    cfg = config()
    client = VirtuosoClient.from_env(profile=cfg["profile"])
    lib = client.library.get(cfg["library"])
    assert lib.path == "/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28"
    assert lib.technology_library == "tsmcN28"
    for cell in (cfg["comparator"], cfg["testbench"], cfg["cdac_testbench"]):
        data = client.schematic.read(cfg["library"], cell, include_positions=False)
        dump(f"readback/{cell}.json", data)
    exports = {}
    for cell in (cfg["testbench"], cfg["cdac_testbench"]):
        r = client.schematic.export_netlist(cfg["library"], cell, OUT / "netlist" / cell,
                                          simulator="spectre", recreate_all=True, timeout=180)
        text = Path(r["input_file"]).read_text(encoding="utf-8")
        exports[cell] = {"path": str(r["input_file"]), "sha256": sha(text),
                         "dut_sha256": sha(dut_block(text))}
        if cell == cfg["testbench"]:
            assert_export(text)
        print("EXPORTED", cell, exports[cell]["dut_sha256"], flush=True)
    old = ROOT / "output/strongarm_t28_first_pass/netlist/tb_sar_strongarm_t28/input.scs"
    baseline_hash = sha(dut_block(old.read_text()))
    assert all(e["dut_sha256"] == baseline_hash for e in exports.values())
    dump("provenance.json", {"library": str(lib), "profile": cfg["profile"],
          "baseline_dut_sha256": baseline_hash, "exports": exports,
          "oa_mutations": [], "scope": "unchanged 11-MOS T28 comparator"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["export","smoke","deterministic","noise-pilot","noise","noise-bandwidth","mc-pilot","mc","mc-binary-pilot","mc-binary","held","integrated","precision","cold-cm"])
    args = parser.parse_args()
    {"export":export,"smoke":lambda:deterministic(True),"deterministic":deterministic,
     "noise-pilot":lambda:noise(True),"noise":noise,"noise-bandwidth":lambda:noise(bandwidth=True),
     "mc-pilot":lambda:mismatch(True),"mc":mismatch,"held":held,
     "mc-binary-pilot":lambda:mismatch_binary(True),"mc-binary":mismatch_binary,
     "integrated":integrated,"precision":precision,"cold-cm":cold_common_mode}[args.stage]()
