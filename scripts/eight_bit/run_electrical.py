"""Run parameterized analyses from exact eight-bit OA exports, never rewrite DUTs."""
from __future__ import annotations

import argparse
import re
import sys

from common import OUT, ROOT, LSB, LIMIT, MACRO_TB, BOOT_TB, COMP_TB, config, stage, run_batch, dump, digest


def prepare(cell, values, analysis, saves, *, tag="initial", clamp=False):
    source = OUT / "oa_netlists" / cell / tag / "input.scs"
    text = source.read_text()
    match = re.search(r"(?m)^parameters ([\w ]+)\s*$", text)
    assert match, "Expected top-level OA design-variable declaration"
    names = match.group(1).split()
    assert set(names) == set(values), (names, values)
    text = text[:match.start()] + "parameters " + " ".join(f"{n}={values[n]:.14g}" for n in names) + text[match.end():]
    for old, new in (("reltol=1e-4","reltol=1e-5"), ("vabstol=1e-6","vabstol=1e-7"),
                     ("iabstol=1e-12","iabstol=1e-13"), ("save=allpub","save=selected")):
        assert text.count(old) == 1, old
        text = text.replace(old,new,1)
    if clamp:
        text += "\nmodel macro_clamp diode is=1e-6 n=1 rs=5\n"
    text += "\n" + analysis + "\nsave " + saves + "\n"
    return text


def macro_cases():
    cfg = config()
    cases = [(f"macro8_code_{code:03d}", -.9+(code+.5)*LSB, {}) for code in cfg["validation"]["nominal_codes"]]
    # Transition-adjacent inputs: +/-0.25 LSB from midscale and a major carry.
    cases += [(f"macro8_near_{code}_{side}", -.9+code*LSB+side*.25*LSB, {}) for code in (64,128) for side in (-1,1)]
    cases += [("macro8_slow_reference", -.9+192.5*LSB, {"RREF":500, "RBOTTOM":1800}),
              ("macro8_top_parasitic", -.9+192.5*LSB, {"CTOPPAR":5e-15}),
              ("macro8_kickback", -.9+192.5*LSB, {"CKB":1e-15})]
    jobs = []
    for name, vin, override in cases:
        params = {"VDIFF":vin,"RBOTTOM":cfg["cdac"]["bottom_ron_ohm"],"RREF":cfg["reference"]["resistance_ohm"],
                  "CDECAP":cfg["reference"]["decoupling_pf"]*1e-12, "CTOPPAR":0, "CKB":.05e-15, **override}
        saves = "TOPP TOPN VREFP VREFN COMP_P COMP_N VALID BUSY CLK_SAMPLE CLK_TRIAL CLK_LATCH CMP_RESET BASE " + " ".join(f"DOUT\\<{b}\\> SEL0\\<{b}\\> SEL1\\<{b}\\>" for b in range(8))
        text = prepare(MACRO_TB, params, "tran tran stop=82n maxstep=5p errpreset=conservative", saves, clamp=True)
        jobs.append(stage(name,text))
        dump(f"electrical/{name}_case.json", {"vdiff_v":vin,"parameters":params,"kind":"nominal" if not override else "sensitivity", "oa_sha256":digest(OUT/"oa_netlists"/MACRO_TB/"initial/input.scs")})
    run_batch(jobs,"electrical",workers=3)


def bootstrap_cases(tag, only_new=False, tight=False):
    cfg=config()
    jobs=[]
    for vd in cfg["validation"]["native_vdiff_v"]:
        if (only_new or tight) and abs(vd)!=.8:continue
        name=f"boot8_{tag}{'_only_new' if only_new else '_tight' if tight else ''}_vd{'m' if vd<0 else 'p'}{abs(round(vd*1000)):03d}"
        params={"VDIFF":vd,"RBOTTOM":cfg["cdac"]["bottom_ron_ohm"]}
        saves="PHI PHIB BASE CLKB_P CLKB_N VCM VDD! "
        saves += " ".join(f"TOP{s}_{v} VIN{s}_{v} X{v}_{s}.G X{v}_{s}.BTOP X{v}_{s}.BBOT X{v}_{s}.CTRL" for v in ("OLD","NEW") for s in ("P","N"))
        saves += " "+" ".join(f"X{v}_{s}.{dev}:currents" for v,dev in (("OLD","MN11"),("NEW","Mmain")) for s in ("P","N"))
        text=prepare(BOOT_TB,params,"tran tran stop=285n maxstep=10p errpreset=conservative",saves,tag=tag)
        if tight:text=text.replace("maxstep=10p","maxstep=5p").replace("reltol=1e-5","reltol=2e-6")
        if only_new:
            sys.path.insert(0,str(ROOT/"scripts/characterization"))
            from compare_canvas_full_cdac import remove_old_branch
            # Explicitly diagnostic-only; primary comparisons use exact OA.
            text=remove_old_branch(text)
            text=re.sub(r"(?m)^save .*", "save "+" ".join(s for s in saves.split() if "OLD" not in s),text)
        jobs.append(stage(name,text))
        dump(f"bootstrap/{name}_case.json", {"vdiff_v":vd,"parameters":params,"oa_tag":tag,"oa_sha256":digest(OUT/"oa_netlists"/BOOT_TB/tag/"input.scs")})
    run_batch(jobs,"bootstrap",workers=3)


def comparator_cases(tag="initial"):
    jobs=[]
    for vd in (-LIMIT,0,LIMIT):
        for enabled in (False,True):
            name=f"comp8_{'' if tag=='initial' else tag+'_'}{'m' if vd<0 else 'p'}{abs(round(vd*1e6)):04d}_{'on' if enabled else 'off'}"
            params={"VDIFF":vd,"RBOTTOM":150,"CMP_HIGH":.9 if enabled else 0}
            text=prepare(COMP_TB,params,"tran tran stop=260n maxstep=5p errpreset=conservative",
                         "TOPP TOPN OUTP OUTN CMP_CLK PHI BASE CLKB_P CLKB_N XNEW_P.G XNEW_N.G",tag=tag)
            jobs.append(stage(name,text))
            dump(f"comparator/{name}_case.json",{"vdiff_v":vd,"clock_enabled":enabled,"parameters":params,
                 "oa_sha256":digest(OUT/"oa_netlists"/COMP_TB/tag/"input.scs")})
    run_batch(jobs,"comparator",workers=3)


def first_order_cases():
    jobs=[]
    for name,resistance,cu,window in (("rc8_nominal",200,6.86047,3), ("rc8_slow",400,6.86047,3),
                                     ("rc8_small_cap",200,.01,3), ("rc8_acquisition",3000,6.86047,40)):
        c=256*cu*1e-15
        stop=(window+2)*1e-9
        text=("// Eight-bit flat first-order half-circuit, double residual for differential comparison\n"
              "simulator lang=spectre\nglobal 0\n"
              "VIN (IN 0) vsource type=pulse val0=0 val1=.9 delay=1n rise=1p fall=1p width=100n period=200n\n"
              f"RPATH (IN OUT) resistor r={resistance}\nCLOAD (OUT 0) capacitor c={c:.14g}\n"
              "simulatorOptions options reltol=1e-7 vabstol=1e-9 iabstol=1e-15 temp=27 tnom=27\n"
              f"tran tran stop={stop:.14g} maxstep=5p errpreset=conservative\nsaveOptions options save=selected\nsave IN OUT\n")
        jobs.append(stage(name,text))
        dump(f"first_order/{name}_case.json",{"resistance_ohm":resistance,"cside_f":c,"window_ns":window})
    run_batch(jobs,"first_order",workers=2)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("action",choices=("macro","bootstrap","candidate-only","tight","first-order","comparator"))
    p.add_argument("--tag",default="initial")
    a=p.parse_args()
    if a.action=="macro":macro_cases()
    elif a.action in ("bootstrap","candidate-only","tight"):bootstrap_cases(a.tag,a.action=="candidate-only",a.action=="tight")
    elif a.action=="comparator":comparator_cases(a.tag)
    else:first_order_cases()


if __name__=="__main__":main()
