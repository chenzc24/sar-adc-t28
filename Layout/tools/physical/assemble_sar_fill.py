"""Import a verified functional core's native density fill and build its OA wrapper."""

from __future__ import print_function
import argparse
import fcntl
import json
import os
from os.path import join
import re

import workspace
from apply_fill import namespaced
import run_physical as native


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("staging", "core_evidence", "utility", "library", "core_view", "wrapper_view"):
        p.add_argument(name)
    p.add_argument("--revision", default="eco2", help="Short namespace for new, immutable OA fill masters")
    p.add_argument("--native-metal", action="store_true", help="Import the foundry utility output directly for top-level density integration")
    p.add_argument("--resistor-channels", action="store_true", help="Include source-bound dummy diffusion between the resistor rows")
    p.add_argument("--header-pins", action="store_true", help="Expose each continuous M5 supply header as the top-level routing pin")
    a = p.parse_args()
    if not re.match(r"\A[a-z][a-z0-9]{0,7}\Z", a.revision):
        raise ValueError("Invalid fill master revision")
    cfg = workspace.paths()
    staging = os.path.realpath(a.staging)
    if os.path.dirname(staging) != cfg["state"] or a.library not in ("SAR_PLACEMENT_WORK", native.LIB):
        raise ValueError("Select an owned SAR staging area and layout library")
    if not all(re.match(r"\Alayout[a-z0-9_]*\Z", v) for v in (a.core_view, a.wrapper_view)):
        raise ValueError("Invalid OA view")
    fill = workspace.evidence(a.utility)
    source = workspace.evidence(a.core_evidence)
    info = json.loads(native.raw(join(fill, "fill_manifest.json")))
    measured = json.loads(native.raw(join(source, "sar-physical.json")))
    original = native.gds_identity(join(workspace.evidence(info["source_evidence"]), "fixture.gds"))
    top = "sar8_sar_timing_core"
    if not (
        info["generation_complete"]
        and info["source_gds_sha256"] == original["sha256"]
        and original["structural_sha256"][top] == measured["geometry_sha256"]
        and (measured["library"], measured["view"]) == (a.library, a.core_view)
    ):
        raise ValueError("Fill and selected native core do not match")
    metal = join(fill, "metal", "fill.gds")
    odpo = join(fill, "ODPO", "fill.gds")
    if a.resistor_channels:
        odpo = join(staging, "resistor-odpo.gds")
        bars = json.loads(native.raw(join(staging, "resistor-odpo.json")))
        if (bars["source_core_sha256"] != original["sha256"] or
                bars["source_odpo_sha256"] != info["steps"]["ODPO"]["gds_sha256"] or
                bars["completed_odpo_sha256"] != native.sha(native.raw(odpo))):
            raise ValueError("Resistor channel fill differs from its native source")
    if not a.native_metal:
        metal = join(staging, "eco-metal.gds")
        delta = json.loads(native.raw(join(staging, "density.json")))
        if delta["source_metal_sha256"] != info["steps"]["metal"]["gds_sha256"] or delta[
            "completed_metal_sha256"
        ] != native.sha(native.raw(metal)):
            raise ValueError("Input density correction has changed")
    out = join(staging, "fill-" + a.library + "-" + a.wrapper_view)
    cds = join(staging, "cds.lib")
    with open(cfg["lock"], "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        os.mkdir(out)
        lib_path = cfg["library_path"] if a.library == native.LIB else join(staging, "private")
        if os.path.exists(join(lib_path, "sar8_sar_timing", a.wrapper_view)):
            raise ValueError("Wrapper view exists")
        for kind, suffix, prefix in (("ODPO", "", "STFO_"), ("metal", "_DM", "STFM_")):
            master = "sar8_timing_fill_" + a.revision + "_" + kind.lower()
            if os.path.exists(join(lib_path, master, "layout")):
                raise ValueError("Native fill master exists")
            utility = join(fill, kind, "fill.gds")
            if native.sha(native.raw(utility)) != info["steps"][kind]["gds_sha256"]:
                raise ValueError("Utility output changed")
            target = join(out, kind + ".gds")
            namespaced(
                odpo if kind == "ODPO" else metal,
                target,
                top + suffix,
                master,
                prefix + a.revision.upper() + "_",
            )
            rc = native.tool(
                native.CADENCE,
                [
                    "strmin",
                    "-library",
                    a.library,
                    "-strmFile",
                    target,
                    "-topCell",
                    master,
                    "-view",
                    "layout",
                    "-cdslib",
                    cds,
                    "-attachTechFileOfLib",
                    "tsmcN28",
                    "-layerMap",
                    join(native.PDK, "tsmcN28.layermap"),
                    "-logFile",
                    join(out, kind + ".log"),
                ],
                out,
                join(out, kind + ".console"),
                180,
            )
            if rc:
                raise RuntimeError("Native import " + kind)
        os.symlink(cds, join(out, "cds.lib"))
        script = join(out, "build.il")
        with open(script, "w") as f:
            f.write(
                'load("%s")\nload("%s")\n'
                % (join(staging, "sar_timing.il"), join(staging, "sar-timing-wrapper.il"))
            )
            f.write(
                'if(errset(stFillWrapper("%s" "%s" "%s" "sar8_timing_fill_%s_odpo" "sar8_timing_fill_%s_metal" %s) t) then exit(0) else exit(1))\n'
                % (a.library, a.wrapper_view, a.core_view, a.revision, a.revision, "t" if a.header_pins else "nil")
            )
        rc = native.tool(
            native.CADENCE,
            ["virtuoso", "-nograph", "-nocdsinit", "-restore", script, "-log", join(out, "wrapper.log")],
            out,
            join(out, "wrapper.console"),
            180,
        )
        if rc or b"SAR_FILL_WRAPPER_OK" not in native.raw(join(out, "wrapper.console")):
            raise RuntimeError("Native wrapper construction failed")
        print(a.library, "sar8_sar_timing", a.wrapper_view)


if __name__ == "__main__":
    main()
