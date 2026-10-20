"""Read-only project/OA inventory; no circuit, UI or source-file mutations.

Writes only generated inventory tables and an ignored raw capture. Run with
the bridge Python and --remote for a fresh DD cell/view metadata listing.
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote

import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = "SAR_ADC_T28"
REMOTE = "/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28"
PROFILE = "t28_io"
os.environ.setdefault("VB_DISABLE_CONTROL_MASTER", "1")


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT).decode("utf-8")


def group_cell(name):
    if name.startswith(("cdac10_dr", "cdac10_dualrail", "tb_cdac10_dr", "tb_cdac10_dualrail")):
        return "10bit新实验_未冻结"
    if name.startswith(("sar8a_", "tb_sar8a_")) or name == "sar_logic_8b_async":
        return "8bit异步控制"
    if name.startswith(("cdac8_dr_", "tb_cdac8_dr_", "cdac8_dualrail_")):
        return "8bit双轨CDAC候选"
    if name.startswith(("cdac8_reset_", "tb_cdac8_reset_")):
        return "8bit复位驱动候选"
    if name.startswith(("cdac8_", "tb_cdac8_")):
        return "8bit器件CDAC与诊断"
    if name in {"sar_bootstrap_canvas_flat_8b", "tb_bootstrap_flat_8b", "tb_cdac_strongarm_flat_8b"}:
        return "8bit采样与接口"
    if name in {"sar_cdac_flat_8b", "sar_macro_controller_8b", "sar_comparator_macro_8b", "tb_sar_macro_flat_8b"}:
        return "8bit电气宏模型"
    if name in {"sar_strongarm_t28", "tb_sar_strongarm_t28"}:
        return "T28比较器_8bit复用"
    if name.startswith(("sar_strongarm_t28_f", "tb_sar_strongarm_t28_f")):
        return "历史比较器尺寸候选"
    if name.startswith("tb_") and ("char" in name or name in {"tb_cdac_ref_settling", "tb_sampling_acquisition", "tb_comparator_regeneration"}):
        return "器件表征与一阶模型"
    if "canvas" in name and "bootstrap" in name:
        return "Canvas自举源拓扑与旧负载"
    if "bottom_plate" in name:
        return "历史10bit底板实验"
    if "bootstrap" in name or "gmain" in name or "pgate" in name:
        return "历史10bit自举实验"
    if name in {"sar_sampling_macro", "sar_comparator_macro", "tb_sar_macro_transient", "tb_sar_cdac_strongarm_diag"} or "10b" in name:
        return "历史10bit模型与宏模型"
    return "其他_查看用途与登记状态"


def file_group(path):
    if "cdac10_dualrail" in path:
        return "10bit新实验_未冻结"
    if "sar8_async" in path or "sar8a_" in path or "sar_async" in path:
        return "8bit异步控制"
    if "sar8_logic" in path or "sar_logic_8b_canvas" in path:
        return "历史8bit同步逻辑提案"
    if "cdac8_dualrail" in path:
        return "8bit双轨CDAC候选"
    if "cdac8_reset" in path:
        return "8bit复位驱动候选"
    if "cdac8_device" in path or "cdac_flat_8b_device" in path:
        return "8bit器件CDAC"
    if "strongarm8" in path:
        return "8bit比较器基线"
    if "eight_bit" in path or "8b.va" in path:
        return "8bit建模迁移与采样"
    if path.startswith(("scripts/characterization/", "scripts/analysis/")) or "bootstrap" in path or "strongarm_t28" in path:
        return "历史表征或共享工具_按报告区分"
    if path.startswith("review/"):
        return "历史10bit审核界面"
    if path.startswith("docs/learning/"):
        return "学习记录"
    if path.startswith("plan/"):
        return "计划与维护日志"
    return "规范文档或共享源_按目录导航"


def write_csv(path, rows, fields):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    path.write_text(stream.getvalue(), encoding="utf-8-sig", newline="")


def capture_remote(rawdir):
    from virtuoso_bridge import VirtuosoClient, decode_skill_output

    client = VirtuosoClient.from_env(profile=PROFILE, timeout=20, log_to_ciw=False)
    info = client.library.get(LIB)
    assert info.path == REMOTE and info.technology_library == "tsmcN28", info
    # Exact DD metadata pattern from basic/04_list_library_cells.py. No OA open/save.
    result = client.execute_skill('''
let((lib out views)
  lib = ddGetObj("SAR_ADC_T28")
  out = ""
  when(lib
    foreach(cell lib~>cells
      views = ""
      foreach(view cell~>views
        views = strcat(views view~>name " "))
      out = strcat(out sprintf(nil "%s|views=%s\\n" cell~>name views))))
  out)
''', timeout=20)
    assert result.status.value == "success", result.errors
    cells = {}
    for row in decode_skill_output(result.output or "").splitlines():
        name, sep, views = row.partition("|views=")
        assert sep and name not in cells, row
        cells[name] = sorted(views.split())
    assert cells, "No live cells returned"
    data = {"captured_at_china": datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds"),
            "name": info.name, "path": info.path, "technology_library": info.technology_library,
            "cells": cells, "read_method": "live bridge DD metadata; not a schematic/ERC audit"}
    # Limited top-level reads establish modeling boundary, not a new simulation.
    probes = {}
    for cell in ("tb_sar8a_strongarm", "tb_sar8a_logic", "sar_logic_8b_async",
                 "tb_cdac8_nominal_sar", "tb_cdac8_dr_strongarm", "cdac8_device_nominal",
                 "sar_bootstrap_canvas_flat_8b", "sar_strongarm_t28"):
        if "schematic" not in cells.get(cell, []):
            continue
        readback = client.schematic.read(LIB, cell, include_positions=False)
        (rawdir / f"{cell}.json").write_text(json.dumps(readback, indent=2, default=str), encoding="utf-8")
        instances = readback.get("instances", [])
        probes[cell] = {"instance_count": len(instances),
                        "masters": sorted({f"{i.get('lib')}/{i.get('cell')}" for i in instances})}
    data["top_level_probes"] = probes
    (rawdir / "remote.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def check_inventory(dest):
    snapshot = json.loads((dest / "snapshot.json").read_text(encoding="utf-8"))
    def rows(name):
        with (dest / name).open(encoding="utf-8-sig", newline="") as stream:
            return list(csv.DictReader(stream))
    local, cells, outputs = rows("local_files.csv"), rows("virtuoso_cells.csv"), rows("output_roots.csv")
    assert len(local) == snapshot["local_files"] == len({r["path"] for r in local})
    assert sum(r["git_state"] == "tracked" for r in local) == snapshot["local_tracked_files"]
    assert sum(r["git_state"] == "untracked" for r in local) == snapshot["local_untracked_files"]
    assert all(r["present"] == "True" and re.fullmatch("[0-9a-f]{64}", r["sha256"]) for r in local)
    actual = [r for r in cells if r["exists_in_live_library"] == "True"]
    assert len(actual) == snapshot["remote_actual_cells"]
    assert len(cells) == len({r["cell"] for r in cells})
    assert dict(sorted(Counter(v for r in actual for v in r["actual_views"].split()).items())) == snapshot["remote_actual_view_counts"]
    assert sorted(r["cell"] for r in actual if r["registered_in_manifest"] == "False") == snapshot["actual_not_in_manifest"]
    assert sorted(r["cell"] for r in cells if r["exists_in_live_library"] == "False") == snapshot["manifest_not_in_actual"]
    assert sum(r["registered_in_manifest"] == "True" for r in cells) == snapshot["manifest_cells"]
    assert len(outputs) == snapshot["output_roots"]
    for doc in (ROOT / "docs/project_status.md", dest / "local_files.md", dest / "virtuoso_cells.md"):
        for match in re.finditer(r"\[[^\]]*\]\(([^)]+)\)", doc.read_text(encoding="utf-8")):
            target = unquote(match[1].split("#")[0])
            if target and not re.match(r"[a-z]+://", target):
                assert (doc.parent / target).exists(), (str(doc), target)
    assert not snapshot["oa_mutations"]
    print(f"CHECK passed: {len(local)} local files, {len(actual)} actual cells, {len(cells)-len(actual)} non-OA entries, all inventory links valid")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--remote", action="store_true")
    parser.add_argument("--check", action="store_true", help="Validate saved tables/links without refreshing")
    parser.add_argument("--date", default="2026-10-20")
    args = parser.parse_args()
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.date)
    dest = ROOT / "docs/inventory" / args.date
    if args.check:
        assert not args.remote
        check_inventory(dest)
        return
    rawdir = ROOT / "output/project_inventory" / args.date
    dest.mkdir(parents=True, exist_ok=True)
    rawdir.mkdir(parents=True, exist_ok=True)
    manifest = yaml.safe_load((ROOT / "virtuoso/cell_manifest.yaml").read_text(encoding="utf-8"))
    remote = capture_remote(rawdir) if args.remote else json.loads((rawdir / "remote.json").read_text(encoding="utf-8"))
    previous = json.loads((dest / "snapshot.json").read_text(encoding="utf-8")) if (dest / "snapshot.json").exists() else {}
    remote_at = remote.get("captured_at_china") or previous.get("remote_readback_at_china") or previous.get("captured_at_china")
    tracked = set(filter(None, git("ls-files", "-z").split("\0")))
    others = set(filter(None, git("ls-files", "--others", "--exclude-standard", "-z").split("\0")))
    local = []
    for name in sorted(tracked | others):
        # The generated inventory lists itself separately, avoiding recursive hashes.
        if name.startswith("docs/inventory/"):
            continue
        path = ROOT / name
        local.append({"path": name, "directory": name.split("/")[0] if "/" in name else "(root)",
                      "group": file_group(name), "git_state": "tracked" if name in tracked else "untracked",
                      "present": path.is_file(), "bytes": path.stat().st_size if path.is_file() else "",
                      "sha256": hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""})
    write_csv(dest / "local_files.csv", local, ["path", "directory", "group", "git_state", "present", "bytes", "sha256"])
    cells = []
    for cell in sorted(set(remote["cells"]) | set(manifest["cells"])):
        entry = manifest["cells"].get(cell, {})
        actual = remote["cells"].get(cell, [])
        cells.append({"cell": cell, "group": group_cell(cell) if actual else "登记计划或本地模型_远端不存在", "exists_in_live_library": cell in remote["cells"],
                      "actual_views": " ".join(actual), "registered_in_manifest": cell in manifest["cells"],
                      "manifest_role": entry.get("role", ""), "manifest_status": entry.get("status", ""),
                      "remote_path": f"{REMOTE}/{cell}" if actual else ""})
    write_csv(dest / "virtuoso_cells.csv", cells, list(cells[0]))
    listing = ["# Virtuoso 设计文件完整清单", "", f"库 `{LIB}`，远端清点时间 `{remote_at}`。",
               "", "以下分类是导航，不是验收状态。`未登记` 表示实际存在但原 manifest 尚未收录；",
               "`远端不存在` 是已登记的计划/本地模型，不能当作可打开的 OA cell。完整字段见 [CSV](virtuoso_cells.csv)。", ""]
    for group in sorted({r["group"] for r in cells}):
        subset = [r for r in cells if r["group"] == group]
        listing += [f"## {group}", "", "| Cell | 实际 view | 登记状态 |", "| --- | --- | --- |"]
        for r in subset:
            views = r["actual_views"] or "远端不存在"
            state = r["manifest_status"] if r["registered_in_manifest"] else "实际存在，原 manifest 未登记"
            listing.append(f"| `{r['cell']}` | {views} | {state} |")
        listing.append("")
    (dest / "virtuoso_cells.md").write_text("\n".join(listing), encoding="utf-8")
    listing = ["# 本地项目源文件完整清单", "", "包括 Git 跟踪文件及未忽略的新文件；Git 状态是清点时快照。",
               "本清单目录自身不递归收录；环境、缓存和逐次仿真原始输出另列，不混入设计源文件。",
               "", "文件大小、分类与 SHA256 见 [CSV](local_files.csv)。", ""]
    for directory in sorted({r["directory"] for r in local}):
        listing += [f"## {directory}", ""]
        for r in local:
            if r["directory"] != directory:continue
            listing.append(f"- [{r['path']}](../../../{r['path']}) — {r['git_state']}{'' if r['present'] else '，磁盘不存在'}")
        listing.append("")
    (dest / "local_files.md").write_text("\n".join(listing), encoding="utf-8")
    outputs = [{"directory": p.relative_to(ROOT).as_posix(), "meaning": "generated evidence; not source-of-truth OA"}
               for p in sorted((ROOT / "output").iterdir()) if p.is_dir()]
    write_csv(dest / "output_roots.csv", outputs, ["directory", "meaning"])
    snapshot = {
        "captured_at_china": datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds"),
        "remote_readback_at_china": remote_at,
        "remote_capture_this_invocation": args.remote,
        "source_commit": git("rev-parse", "HEAD").strip(), "branch": git("branch", "--show-current").strip(),
        "local_root": str(ROOT), "source_list_scope": "all tracked and nonignored untracked files except docs/inventory itself",
        "local_files": len(local), "local_tracked_files": sum(x["git_state"] == "tracked" for x in local),
        "local_untracked_files": sum(x["git_state"] == "untracked" for x in local),
        "local_counts_by_directory": dict(sorted(Counter(x["directory"] for x in local).items())),
        "remote_library": {k: v for k, v in remote.items() if k != "cells"},
        "remote_actual_cells": len(remote["cells"]),
        "remote_actual_view_counts": dict(sorted(Counter(v for views in remote["cells"].values() for v in views).items())),
        "manifest_cells": len(manifest["cells"]),
        "actual_not_in_manifest": sorted(set(remote["cells"]) - set(manifest["cells"])),
        "manifest_not_in_actual": sorted(set(manifest["cells"]) - set(remote["cells"])),
        "remote_groups": dict(sorted(Counter(group_cell(c) for c in remote["cells"]).items())),
        "output_roots": len(outputs), "oa_mutations": [],
        "safety": "No moves, deletions, saves, category changes, simulations or connection repair."
    }
    (dest / "snapshot.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in snapshot.items() if k not in {"remote_library", "local_counts_by_directory"}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
