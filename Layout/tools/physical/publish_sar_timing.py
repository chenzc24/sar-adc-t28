"""Copy a routed SAR into a fresh OA view, optionally attaching native dummy fill."""

from __future__ import print_function

import argparse
import fcntl
import json
import os
import re
from os.path import join

import workspace
from apply_fill import namespaced
from run_physical import CADENCE, PDK, gds_identity, raw, sha, tool


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("staging")
    parser.add_argument("source_evidence")
    parser.add_argument("source_library")
    parser.add_argument("source_view")
    parser.add_argument("view")
    parser.add_argument("--fill")
    args = parser.parse_args()
    cfg = workspace.paths()
    stage = os.path.realpath(args.staging)
    if os.path.dirname(stage) != cfg["state"]:
        raise ValueError("Staging must be an owned layout job")
    for name in (args.source_library, args.source_view, args.view):
        if not re.match(r"\A[A-Za-z0-9_]+\Z", name):
            raise ValueError("Invalid OA identifier")
    if args.view == "layout":
        raise ValueError("Select a new named view to preserve the original layout")
    core = "sar8_sar_timing_core"
    library = "SAR_ADC_T28_LAYOUT"
    src = workspace.evidence(args.source_evidence)
    record = json.loads(raw(join(src, "sar-physical.json")))
    if (record["library"], record["cell"], record["view"]) != (
        args.source_library,
        core,
        args.source_view,
    ):
        raise ValueError("Evidence does not identify the requested source view")
    count = len(re.findall(br"(?m)^INST ", raw(join(src, "sar-readback.txt"))))
    if not count or len(record["labels"]) != 26:
        raise ValueError("Incomplete native core readback")
    with open(cfg["lock"], "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        out = join(stage, args.view)
        os.mkdir(out)
        cds = join(stage, "cds.lib")
        if os.path.exists(join(cfg["library_path"], core, args.view)):
            raise ValueError("Destination OA view already exists")
        current = join(out, "source.gds")
        rc = tool(
            CADENCE,
            [
                "strmout",
                "-library",
                args.source_library,
                "-topCell",
                core,
                "-view",
                args.source_view,
                "-strmFile",
                current,
                "-cdslib",
                cds,
                "-layerMap",
                join(PDK, "tsmcN28.layermap"),
                "-runDir",
                out,
                "-logFile",
                join(out, "stream.log"),
                "-convertPin",
                "geometry",
                "-convertPcellPin",
                "geometry",
            ],
            stage,
            join(out, "stream.console"),
            180,
        )
        if rc or gds_identity(current)["structural_sha256"][core] != record["geometry_sha256"]:
            raise ValueError("Native source geometry differs from its verified stream")
        add_fill = []
        if args.fill:
            folder = workspace.evidence(args.fill)
            result = json.loads(raw(join(folder, "fill_manifest.json")))
            verified = workspace.evidence(result["source_evidence"])
            verified_gds = gds_identity(join(verified, "fixture.gds"))
            if (
                not result["generation_complete"]
                or result["top"] != core
                or verified_gds["sha256"] != result["source_gds_sha256"]
                or verified_gds["structural_sha256"][core] != record["geometry_sha256"]
            ):
                raise ValueError("Fill was generated for a different core")
            for kind, suffix, prefix in (("ODPO", "", "STFO_"), ("metal", "_DM", "STFM_")):
                original = join(folder, kind, "fill.gds")
                if sha(raw(original)) != result["steps"][kind]["gds_sha256"]:
                    raise ValueError("Dummy stream changed")
                name = "sar8_timing_fill_" + kind.lower()
                if os.path.exists(join(cfg["library_path"], name, "layout")):
                    raise ValueError("Fill master already exists")
                target = join(out, kind + ".gds")
                namespaced(original, target, core + suffix, name, prefix)
                rc = tool(
                    CADENCE,
                    [
                        "strmin",
                        "-library",
                        library,
                        "-strmFile",
                        target,
                        "-topCell",
                        name,
                        "-view",
                        "layout",
                        "-cdslib",
                        cds,
                        "-attachTechFileOfLib",
                        "tsmcN28",
                        "-layerMap",
                        join(PDK, "tsmcN28.layermap"),
                        "-logFile",
                        join(out, kind + ".log"),
                    ],
                    stage,
                    join(out, kind + ".console"),
                    180,
                )
                if rc:
                    raise RuntimeError("Native fill import failed for " + kind)
                add_fill.extend(
                    [
                        'master=dbOpenCellViewByType("%s" "%s" "layout" "" "r")' % (library, name),
                        'stNeed(master && dbCreateInst(cv master "FILL_%s" 0:0 "R0") "Missing fill")'
                        % kind.upper(),
                        "dbClose(master)",
                    ]
                )
        lines = (
            [
                'load("sar_timing.il")',
                "procedure(stPublish() let((src cv master)",
                'src=dbOpenCellViewByType("%s" "%s" "%s" "" "r")'
                % (args.source_library, core, args.source_view),
                'stNeed(src && length(src~>instances)==%d && length(src~>terminals)==26 "Unexpected source")' % count,
                'stNeed(!ddGetObj("%s" "%s" "%s") "Destination exists")' % (library, core, args.view),
                'cv=dbCopyCellView(src "%s" "%s" "%s")' % (library, core, args.view),
                'stNeed(cv "Native copy failed")',
            ]
            + add_fill
            + [
                'stNeed(dbSave(cv) "Save failed")',
                "dbClose(cv) dbClose(src)",
                'stAudit("%s" "%s" "%s")' % (library, core, args.view),
                'printf("SAR_PUBLISHED\\n") t))',
                "if(errset(stPublish() t) then exit(0) else exit(1))",
            ]
        )
        il = join(out, "publish.il")
        with open(il, "w") as script:
            script.write("\n".join(lines) + "\n")
        rc = tool(
            CADENCE,
            ["virtuoso", "-nograph", "-nocdsinit", "-log", join(out, "publish.log"), "-restore", il],
            stage,
            join(out, "publish.console"),
            180,
        )
        if rc or b"SAR_PUBLISHED" not in raw(join(out, "publish.console")):
            raise RuntimeError("Native publish failed. Inspect " + out)
        print(library, core, args.view)


if __name__ == "__main__":
    main()
