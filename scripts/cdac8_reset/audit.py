"""Final OA identity and strict no-change verification of original designs."""
from __future__ import annotations

import argparse
import json
import re

from support import LIB, OUT, ROOT, dump, sha
from oa_candidate import check, export
from virtuoso_bridge import VirtuosoClient


def canonical(text):
    return "\n".join(line for line in text.splitlines() if not line.startswith("// Generated on:"))


def source_audit():
    c = VirtuosoClient.from_env(profile="t28_io")
    rows = []
    for cell in ("cdac8_controller", "cdac8_device_sequence"):
        path = f"/home/chenzc_intern25/TSMC28/llm_IO/{LIB}/{cell}/veriloga/veriloga.va"
        result = c.ssh_runner.run_command(f"sha256sum '{path}'", timeout=30)
        actual = result.stdout.split()[0]
        assert actual == sha(ROOT / f"models/veriloga/{cell}.va"), cell
        rows.append({"cell": cell, "local_remote_equal_sha256": actual})
    dump("source_audit.json", {"veriloga": rows})
    print("SOURCE_AUDIT_OK", len(rows))


def main(export_tag="final_audit"):
    assert re.fullmatch(r"[A-Za-z0-9_-]+", export_tag)
    c = VirtuosoClient.from_env(profile="t28_io")
    info = c.library.get(LIB)
    assert info.path == "/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28" and info.technology_library == "tsmcN28"
    preserved = []
    for path in sorted((OUT / "preflight").glob("*.json")):
        if path.stem in ("library", "windows"):
            continue
        state = c.schematic.read(LIB, path.stem, param_filters=None, include_positions=True)
        assert state == json.loads(path.read_text()), f"Read-only dependency changed: {path.stem}"
        preserved.append(path.stem)
    checked = []
    for path in sorted((OUT / "oa").glob("*.json")):
        cell = path.stem
        if cell.endswith(("_markers", "_export")):
            continue
        state = c.schematic.read(LIB, cell, param_filters=None, include_positions=True)
        assert state == json.loads(path.read_text()), f"Candidate drift: {cell}"
        check(c, cell)
        checked.append(cell)
    exports = []
    for cell in ("tb_cdac8_reset_nominal", "tb_cdac8_reset_literal", "tb_cdac8_reset_strongarm"):
        source = OUT / "oa_netlists" / cell / "primary/input.scs"
        if not source.exists():
            continue
        export(c, cell, export_tag)
        fresh = source.parent.parent / export_tag / "input.scs"
        assert canonical(fresh.read_text()) == canonical(source.read_text()), cell
        exports.append({"cell": cell, "fresh_equal_except_timestamp": True, "sha256": sha(fresh)})
    va = []
    for cell in ("cdac8_controller", "cdac8_device_sequence"):
        path = f"/home/chenzc_intern25/TSMC28/llm_IO/{LIB}/{cell}/veriloga/veriloga.va"
        result = c.ssh_runner.run_command(f"sha256sum '{path}'", timeout=30)
        actual = result.stdout.split()[0]
        assert actual == sha(ROOT / f"models/veriloga/{cell}.va"), cell
        va.append({"cell": cell, "local_remote_sha256_equal": actual})
    dump("audit.json", {"preserved_dependencies": preserved, "zero_marker_cells": checked,
                         "fresh_exports": exports, "library_verified": True, "va_sources_equal": va})
    print("AUDIT_OK", len(preserved), "preserved;", len(checked), "zero-marker schematics;", len(exports), "fresh equal exports")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources-only", action="store_true")
    parser.add_argument("--export-tag", default="final_audit")
    args = parser.parse_args()
    source_audit() if args.sources_only else main(args.export_tag)
