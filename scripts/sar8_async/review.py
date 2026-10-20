"""Final saved-state provenance and opening only this target's review cells."""
import argparse
import hashlib
import json
import shlex
from circuit import LIB
from oa import ROOT,OUT,dump
from audit import normalized_blocks
from simulate import source
from virtuoso_bridge import VirtuosoClient


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--open",action="store_true");args=ap.parse_args()
    c=VirtuosoClient.from_env(profile="t28_io")
    old=json.loads((OUT/"dependency_strongarm_before.json").read_text(encoding="utf-8"))
    new=c.schematic.read(LIB,"sar_strongarm_t28",param_filters=None)
    assert old==new,"Read-only comparator changed"
    dump("dependency_strongarm_after.json",new)
    exports={}
    for cell in ("tb_sar8a_logic","tb_sar8a_strongarm","tb_sar8a_gates"):
        fresh=source(cell,"human_final");accepted=source(cell,"recovery")
        a,b=normalized_blocks(fresh),normalized_blocks(accepted)
        assert a==b,(cell,"Final saved hierarchy differs from simulated export")
        exports[cell]=dict(accepted_sha256=hashlib.sha256(accepted.encode()).hexdigest(),
                          fresh_sha256=hashlib.sha256(fresh.encode()).hexdigest(),
                          native_subcircuits_equal=True)
    local=ROOT/"models/veriloga/sar8a_plant.va"
    remote=c.library.get(LIB).path+"/sar8a_plant/veriloga/veriloga.va"
    r=c.ssh_runner.run_command("sha256sum "+shlex.quote(remote),timeout=30)
    digest=hashlib.sha256(local.read_bytes()).hexdigest()
    assert r.stdout.split()[0]==digest,r
    dump("audit/final_saved_state.json",dict(comparator_unchanged=True,exports=exports,
                                            plant_local_remote_sha256=digest))
    if args.open:
        for cell in ("sar8a_dffr","sar8a_seq","sar_logic_8b_async"):
            result=c.open_window(LIB,cell,view="schematic",timeout=60)
            assert not result.errors,result.errors
            windows=[w for w in c.list_windows() if cell+" " in w["name"]]
            assert len(windows)==1,(cell,windows)
            image=c.screenshot(OUT/"review"/(cell+".png"),target=int(windows[0]["num"]),timeout=90)
            assert not image.errors,image.errors
            print("OPEN_REVIEW",cell,windows[0]["num"],flush=True)
        dump("review/windows.json",c.list_windows())
    print("FINAL_SAVED_STATE_OK",flush=True)


if __name__=="__main__":main()
