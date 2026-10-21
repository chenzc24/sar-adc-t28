"""Plot the saved reference-timer A/B replay; no simulation or source edits."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import pickle

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Obsidian_docs/assets/wrapup_timer"
EVIDENCE = ROOT / "verification/integration/r3_refgate_events_results.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_wave(folder, record):
    base = ROOT / "output/r3_refgate_events" / folder
    path = base / "waveform.pickle"
    receipt = json.loads((base / "waveform_receipt.json").read_text())
    digest = sha(path)
    assert digest == receipt["sha256"] == record["provenance"]["waveform_sha256"]
    with path.open("rb") as stream:
        raw = pickle.load(stream)  # trusted project output, verified above
    names = ["time", "sample", "topp", "topn", "vinp_src", "vinn_src",
             "xdut.xcdac.bn7"] + [f"d{bit}" for bit in range(8)]
    w = {k: np.asarray(raw[k], dtype=float) for k in names}
    del raw
    t = w.pop("time") * 1e9
    assert len(t) == receipt["points"] and np.all(np.diff(t) > 0)
    assert all(len(v) == len(t) and np.isfinite(v).all() for v in w.values())
    frame = record["frames"][0]
    assert frame["frame"] == 8
    at = lambda signal, ns: float(np.interp(ns, t, w[signal]))
    source = frame["source_diff_v"]
    assert abs(at("vinp_src", 841.05) - at("vinn_src", 841.05) - source) < 1e-12
    error = (w["topp"] - w["topn"] - source) * 1000
    held = float(np.interp(841.65, t, error))
    code = sum(int(at(f"d{bit}", 898) > .45) << bit for bit in range(8))
    assert abs(held - frame["held_offset_0p6ns_mv"]) < 1e-7
    assert code == frame["output_code"]
    assert abs(at("sample", 841.05) - .45) < 1e-7
    assert frame["comparisons"][0]["compare_ns"] > 843.5
    metrics = dict(waveform_sha256=digest, frame=9, held_read_ns=841.65,
                   held_error_mv=held, read_ns=898, output_code=code,
                   source_diff_v=source, first_compare_ns=frame["comparisons"][0]["compare_ns"])
    return t, w, error, metrics


def main():
    evidence = json.loads(EVIDENCE.read_text())
    assert evidence["inputs_identical"] and evidence["parameters_identical"]
    assert evidence["native_SAR_and_analog_topology_sizes_unchanged"]
    records = {"A": load_wave("a", evidence["A"]),
               "B": load_wave("b3", evidence["B"])}
    rejection = next(r for r in evidence["A"]["near_deadline_A_restore_rejections"]
                     if r["instance"] == "XDUT.XGN7")
    assert .15 < rejection["early_fs"] < .17 and rejection["restored"] == 0
    plt.rcParams.update({"font.family": "Microsoft YaHei", "font.size": 11,
                         "axes.unicode_minus": False, "axes.spines.top": False,
                         "axes.spines.right": False, "svg.fonttype": "path"})
    colors = {"A": "#c44d43", "B": "#148278"}
    fig, axes = plt.subplots(3, 2, figsize=(13.5, 8.2), sharex="col",
                             gridspec_kw={"height_ratios": [0.65, 1, 1.35],
                                          "width_ratios": [1.25, 1]})
    fig.subplots_adjust(left=.095, right=.97, bottom=.09, top=.73,
                        wspace=.23, hspace=.25)
    fig.text(.095, .96, "参考恢复迟到，扰动已保持电荷", fontsize=20, weight="bold", va="top")
    fig.text(.095, .906, "T28 TT · VDD 0.9 V · 27°C · 10 MS/s ｜ 原历史完整重放 12 帧，图示第 9 帧", fontsize=10)
    fig.text(.095, .871, "管级：Bootstrap / MOM / 3×参考开关 / StrongARM / SAR；理想：参考栅控 / COMMIT / 外部采样与供电", fontsize=9.5)
    fig.text(.095, .839, "输入 −442.529 mV；每侧输入 50 Ω，参考每轨 50 Ω＋4 pF；无噪声／失配；A/B 仅改参考栅控事件处理", fontsize=9.5)
    fig.legend(handles=[Line2D([], [], color=colors["A"], lw=2, label="A：修复前"),
                        Line2D([], [], color=colors["B"], lw=2, label="B：修复后"),
                        Line2D([], [], color="#69717b", lw=1.1, ls="--", label="预期基准")],
               loc="upper left", bbox_to_anchor=(.09, .819), ncol=3, frameon=False, fontsize=10)
    windows = [(800.9, 843.5), (840.95, 842.2)]
    for col, (lo, hi) in enumerate(windows):
        axes[0, col].set_title("完整采样窗口" if col == 0 else "关断附近放大", loc="left", fontsize=12, pad=10)
        for key, (t, w, error, metrics) in records.items():
            mask = (t >= lo) & (t <= hi)
            if key == "A":
                axes[0, col].plot(t[mask], w["sample"][mask], color="#343d4a", lw=1.7)
            axes[1, col].plot(t[mask], w["xdut.xcdac.bn7"][mask], color=colors[key], lw=1.9)
            axes[2, col].plot(t[mask], error[mask], color=colors[key], lw=1.9)
        for row in range(3):
            a = axes[row, col]
            a.axvspan(max(lo, 801.05), 841.05, color="#eef5f0", zorder=-4)
            a.axvspan(841.05, hi, color="#edf1f5", zorder=-4)
            a.axvline(841.05, color="#83909c", lw=1, ls=":")
            a.grid(axis="y", alpha=.18)
            a.set_xlim(lo, hi)
        axes[0, col].set_ylim(-.12, 1.12)
        axes[0, col].set_yticks([0, .9])
        axes[1, col].axhline(.9, color="#69717b", lw=1, ls="--", zorder=3)
        axes[1, col].set_ylim(-.08, 1.08)
        axes[1, col].set_yticks([0, .45, .9])
        axes[2, col].axhline(0, color="#69717b", lw=1, ls="--", zorder=3)
        axes[2, col].set_ylim(-630, 520)
        axes[2, col].set_yticks([-500, 0, 500])
        axes[2, col].set_xlabel("绝对时间（ns）")
    axes[0, 0].set_ylabel("SAMPLE\n（V）")
    axes[1, 0].set_ylabel("N7 底板\n（V）")
    axes[2, 0].set_ylabel("顶板差模 − 输入\n（mV）")
    axes[0, 0].text(820, .33, "采样开关接通 · 40 ns", ha="center", color="#4b6254", fontsize=10)
    axes[0, 1].text(841.58, .45, "保持，尚未比较", ha="center", color="#536273", fontsize=10)
    axes[0, 1].annotate("关断命令", xy=(841.05, .45), xytext=(841.2, 1.0),
                        arrowprops={"arrowstyle": "-", "color": "#687789"}, fontsize=9)
    axes[1, 0].text(820, .68, "B：获取初期完成恢复", color=colors["B"], ha="center", fontsize=11)
    axes[1, 0].text(820, .16, "A：整段采样仍留在上帧连接", color=colors["A"], ha="center", fontsize=11)
    axes[1, 1].text(841.48, .4, "A 此时才恢复", color=colors["A"], ha="center", fontsize=10)
    axes[2, 1].set_ylim(-620, 65)
    axes[2, 1].set_yticks([-600, -400, -200, 0])
    for key, (_, _, _, m) in records.items():
        axes[2, 1].plot(841.65, m["held_error_mv"], "o", color=colors[key], ms=5, zorder=5)
    axes[2, 1].annotate("B：+0.101 mV", xy=(841.65, records["B"][3]["held_error_mv"]),
                        xytext=(841.52, 30), color=colors["B"], fontsize=10,
                        arrowprops={"arrowstyle": "-", "color": colors["B"]})
    axes[2, 1].annotate("A：−442.850 mV", xy=(841.65, records["A"][3]["held_error_mv"]),
                        xytext=(841.38, -270), color=colors["A"], fontsize=10,
                        arrowprops={"arrowstyle": "->", "color": colors["A"]})
    axes[2, 1].text(841.64, -565, "圆点：841.65 ns 保持值", ha="center", color="#536273", fontsize=9)
    axes[2, 0].set_xticks([801.05, 810, 820, 830, 841.05])
    axes[2, 0].set_xticklabels(["801.05", "810", "820", "830", "841.05"])
    axes[2, 1].set_xticks([841.05, 841.5, 842])
    axes[2, 1].set_xticklabels(["841.05", "841.50", "842.00"])
    OUT.mkdir(parents=True, exist_ok=True)
    for suffix in ("png", "svg"):
        path = OUT / f"timer_restore.{suffix}"
        fig.savefig(path, dpi=180, facecolor="white")
        if suffix == "svg":
            path.write_text("\n".join(line.rstrip() for line in path.read_text(encoding="utf-8").splitlines()) + "\n", encoding="utf-8")
    plt.close(fig)
    manifest = dict(generator="scripts/reporting/wrapup_timer_figure.py",
                    generator_sha256=sha(Path(__file__)), evidence=str(EVIDENCE.relative_to(ROOT)),
                    evidence_sha256=sha(EVIDENCE), variants={k: data[3] for k, data in records.items()},
                    rejected_callback=rejection, windows_ns=windows,
                    waveform_data_modified=False, new_simulation=False,
                    error_definition="(TOPP-TOPN)-constant frame9 source; hold read 841.65ns",
                    reference_example="N7 bottom should connect to VREFP, not VCM",
                    figure_sha256={s: sha(OUT / f"timer_restore.{s}") for s in ("png", "svg")})
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: data[3] for k, data in records.items()}, indent=2))


if __name__ == "__main__":
    main()
