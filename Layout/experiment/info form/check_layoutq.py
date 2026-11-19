"""Exercise the installed CLI on local frozen inputs. Run with layout-query-kit[gds]."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / "work/layout"
RUN = Path(os.environ.get("LAYOUTQ_REGRESSION_DIR", WORK / "layoutq-regression"))
IMPORTER = WORK / "layoutml-v3-preview/LayoutML/explorations/Q-tech-decoupling/gds_to_lml_algo.py"
PROFILE = ROOT / "Layout/specs/layout-query-t28.json"
CATALOG = WORK / "layoutml-migration-survey/runs.json"


def cli(*args, expected=0):
    result = subprocess.run(
        [sys.executable, "-m", "layoutq", *map(str, args)],
        cwd=ROOT, capture_output=True, timeout=300,
    )
    if result.returncode != expected:
        raise RuntimeError(f"{args[0]} exit {result.returncode}: {(result.stderr or result.stdout)[-1600:]!r}")
    return json.loads(result.stdout if expected != 2 else result.stderr)


def main():
    runs = json.loads(CATALOG.read_text())
    RUN.mkdir(parents=True, exist_ok=True)
    report = {}
    for name in ("v3", "v4", "v6", "v7", "bootstrap", "cdac", "v4-swapped-gate"):
        case = runs[name]
        gds, cdl = ROOT / case["gds"], ROOT / case["cdl"]
        args = ("build", gds, cdl, "--importer", IMPORTER, "--cache", RUN / "cache")
        start = time.perf_counter()
        build = cli(*args)
        row = {"input_sha256": build["input_sha256"], "query_status": build["query_status"],
               "build_s": time.perf_counter()-start, "cache_hit": build["cache_hit"]}
        directory = build["snapshot"]
        assert cli(*args)["cache_hit"]
        physical = ("--gds", gds, "--profile", PROFILE)
        partial = name in ("bootstrap", "v4-swapped-gate")
        audit = cli("audit", directory, cdl, expected=int(partial))
        assert audit["ok"] == (not partial)
        row["audit"] = audit
        if name in ("v3", "v4", "v6", "v7"):
            row["geometry"] = [cli("verify-net", directory, n, *physical) for n in ("OUTP","OUTN")]
            assert all(check["ok"] for check in row["geometry"])
        if name == "v4":
            pair = cli("pair", directory, "OUTP", "OUTN")
            row["max_mirror_nm"] = max(abs(m["delta_nm"]) for m in pair["matched_segments"])
            assert row["max_mirror_nm"] == 240 and not pair["unpaired_groups"]
            assert "digest" in cli("physical", directory, "OUTP", "--profile", PROFILE, "--gds",
                                    ROOT / runs["v3"]["gds"], expected=2)["error"]
            changed = WORK / "layoutml-migration-survey/controls/v4-minus-10nm.gds"
            new = cli("build", changed, cdl, "--importer", IMPORTER, "--cache", RUN / "cache")
            lengths = [cli("net", path, "OUTP")["length_nm_by_layer"]["M2"]
                       for path in (directory,new["snapshot"])]
            row["shortening_nm"] = lengths[0] - lengths[1]
            assert row["shortening_nm"] == 10
        if name in ("bootstrap","cdac"):
            row["caps"] = cli("verify-caps", directory, *physical)
            assert row["caps"]["ok"] and row["caps"]["mapped"] == (680 if name=="cdac" else 200)
        if name=="cdac":
            for net in ("TOPP","TOPN"):
                assert cli("net", directory, net)["stacks"] == 0
                row[net] = cli("physical", directory, net, *physical)
                assert row[net]["cuts_by_layer"]["V1"]==1280 and row[net]["cuts_by_layer"]["V2"]==1024
                covered=cli("verify-caps",directory,*physical,"--net",net)["store_cut_coverage"]
                assert all(layer["outside_cap_store_area_nm2"]==0 for layer in covered["layers"].values())
                row[net]["capacitor_store"]=covered
        if name=="v4-swapped-gate":
            assert any(i["device"]=="MNINP" for i in audit["mos_issues"])
        report[name]=row
        (RUN/"results.json").write_text(json.dumps(report,indent=2),encoding="utf8")
        print(name, build["query_status"], flush=True)


if __name__ == "__main__":
    main()
