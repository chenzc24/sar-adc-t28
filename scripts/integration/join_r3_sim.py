"""Fresh confirmations from the saved R3 export; never patch DUT statements."""
from __future__ import annotations
import argparse
import re

import join_r1_sim
import reference_edge_slew as runner
from join_r3 import ROOT,OUT,TOP,OLD_TOP,VAS,GATE,COMMIT,dump,r1,audit_export

POINTS=("nfull","pfull","n_to_p","p_to_n")
VALUES={"nfull":(-.8,-.8),"pfull":(.8,.8),"n_to_p":(-.8,.8),"p_to_n":(.8,-.8)}


def normalize_subckts(text,top):
    blocks=r1.blocks(text)
    blocks["<TOP>"]=blocks.pop(top)
    return blocks


def prepare():
    export=OUT/"exports/primary/input.scs"
    assert r1.sha(export)==r1.read_json(OUT/"exports/primary/audit.json")["export_sha256"]
    source=export.read_text();audit_export(source);before=r1.blocks(source)
    manifest=r1.read_json(ROOT/"verification/integration/reference_edge_slew_results.json")
    for point in POINTS:
        v0,v1=VALUES[point];text=source
        def variables(match):
            keys=match[1].replace("\\","").split();values={"SUP":.9,"VDIFF":v0}
            assert set(keys)<=values.keys()
            return "parameters "+" ".join(f"{k}={values[k]:.14g}" for k in keys)
        text,n=re.subn(r"(?m)^parameters (.*(?:\n[ \t]+.*)*)",variables,text);assert n==1
        if v0!=v1:
            for side,sign in (("P",1),("N",-1)):
                a=.45+sign*v0/2;b=.45+sign*v1/2
                statement=(f"VVIN{side} (VIN{side}_SRC 0) vsource dc={a:.14g} type=pwl "
                    f"wave=[0 {a:.14g} 100.8n {a:.14g} 100.9n {b:.14g} 200n {b:.14g}]")
                text,n=re.subn(rf"(?m)^VVIN{side} \([^\n]+$",statement,text);assert n==1
        text=text.replace("save=allpub","save=selected").replace("reltol=1e-4","reltol=1e-5")
        text=text.replace("vabstol=1e-6","vabstol=1e-8").replace("iabstol=1e-12","iabstol=1e-13")
        text=re.sub(r"(?m)^\w+ info [^\n]*\n","",text)
        includes=re.findall(r'(?m)^ahdl_include "([^"]+)"',text);assert len(includes)==2
        for name,path in VAS.items():
            old=next(p for p in includes if p.endswith(f"/{name}/veriloga/veriloga.va"))
            text=text.replace(f'ahdl_include "{old}"',f'ahdl_include "{path.name}"')
        assert r1.blocks(text)==before,"DUT modified in simulation wrapper"
        saves=join_r1_sim.signals()+["XDUT.GCOMMIT","XDUT.XCOMP.X","XDUT.XCOMP.Y","XDUT.XCOMP.TAIL"]
        text+="\ntran_join tran stop=200n maxstep=10p errpreset=conservative\n"
        text+="save "+" ".join(saves)+"\n"
        path=OUT/f"decks/{point}.scs";assert not path.exists(),"Immutable case: "+point
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding="utf-8")
        prior=next(r for r in manifest["cases"] if r["point"]==point and r["edge_ps"]==50)
        priorpath=ROOT/prior["source_folder"]/f"decks/{prior['source_case']}.scs"
        assert r1.sha(priorpath)==prior["context"]["deck_sha256"]
        assert normalize_subckts(text,TOP)==normalize_subckts(priorpath.read_text(),OLD_TOP)
        dump(f"cases/{point}.json",dict(name=point,point=point,export_sha256=r1.sha(export),
            deck_sha256=r1.sha(path),gate_va_sha256=r1.sha(VAS[GATE]),commit_va_sha256=r1.sha(VAS[COMMIT]),
            stimulus_vdiff_by_frame=[v0,v1],stimulus_transition_ns=[100.8,100.9] if v0!=v1 else None,
            supply_v=.9,temperature_c=27,corner="tt",MOM_corner="tt",resolution_bits=8,sample_rate_hz=10e6,
            stop_ns=200,maxstep_ps=10,output_strobe_ps=0,saved_signals=saves,
            native_controller=True,native_StrongARM=True,native_Bootstrap=True,
            native_MOM_and_3x_reference_pass_MOS=True,ideal_DAC_plant=False,
            physical_noise=False,mismatch=False,restore_guard_ps=100,edge_ps=50,
            exact_saved_OA_DUT_unmodified=True,
            prior_candidate_case=prior["source_case"],prior_candidate_deck_sha256=r1.sha(priorpath),
            scope="fresh_saved_R3_OA_DUT_stimulus_analysis_wrapper_only"))
        print("PREPARED",point,flush=True)


def run(names):
    # Reuse the bounded-memory native APS runner; existing source stays unedited.
    runner.OUT=OUT;runner.dump=dump
    runner.run(names)


if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("action",choices=["prepare","run"])
    ap.add_argument("names",nargs="*");a=ap.parse_args()
    if a.action=="prepare":prepare()
    else:run(a.names or list(POINTS))
