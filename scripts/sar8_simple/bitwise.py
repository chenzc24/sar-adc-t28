"""Plot all token/SAR bits and observed ideal-plant approximation, offline only."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np

from analyze import edges, load
from oa import OUT, ROOT
from plot import envelope, save

NAME = "two_cycles_simple_v2_aps"
SPAN_V = 1.8
TOKEN_COLOR, WORD_COLOR = "#2673b8", "#b36317"
DAC_COLOR, RESIDUAL_COLOR = "#76519a", "#267e75"
CLOCKS = [("sample", "SAMPLE"), ("cmp_clk", "CMP_CLK"),
          ("xctrl.phi_w", "PHI_W"), ("xctrl.phi_u", "PHI_U")]


def font_setup():
    font = Path("C:/Windows/Fonts/msyh.ttc")
    if font.exists():
        font_manager.fontManager.addfont(str(font))
        plt.rcParams["font.family"] = font_manager.FontProperties(fname=str(font)).get_name()
    plt.rcParams.update({"font.size": 10, "axes.unicode_minus": False,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "svg.hashsalt": "sar8-bitwise-v1"})


def extract():
    record, context, data, digest = load(NAME)
    pinned = json.loads((ROOT / "verification/sar8_simple/summary.json").read_text(encoding="utf-8"))
    case = next(row for row in pinned["cases"] if row["name"] == NAME)
    assert digest == case["waves_sha256"] and context == case["context"]
    assert record["ok"] and not context["physical_cdac"]
    analysis = json.loads((OUT / "analysis" / (NAME + ".json")).read_text(encoding="utf-8"))
    assert analysis["waves_sha256"] == digest
    t, supply = data["time"] * 1e9, context["supply_v"]
    assert np.all(np.diff(t) > 0)
    level = supply / 2
    at = lambda key, when: float(np.interp(when, t, data[key]))
    word = lambda prefix, when: sum((1 << bit) * int(at(prefix + str(bit), when) > level)
                                    for bit in range(8))
    # Require complementary, rail-settled P/N choices. Sampling/BBM gaps are
    # not physical capacitor behavior in this ideal algebraic DAC plant.
    valid = data["sample"] < .1 * supply
    for bit in range(8):
        ph, pl, nh, nl = [data[f"b{bank}_{rail}{bit}"] for bank, rail in
                          (("p", "h"), ("p", "l"), ("n", "h"), ("n", "l"))]
        one = (ph > .9*supply) & (pl < .1*supply) & (nh < .1*supply) & (nl > .9*supply)
        zero = (ph < .1*supply) & (pl > .9*supply) & (nh > .9*supply) & (nl < .1*supply)
        valid &= one | zero
    frames = []
    held = np.full_like(t, np.nan)
    residual = data["topp"] - data["topn"]
    writes = edges(t, data["xctrl.phi_w"], level)
    for number, src in enumerate(analysis["frames"], start=1):
        start, end = src["sample_end_ns"], src["next_sample_ns"]
        observed_writes = writes[(writes > start) & (writes < end)]
        assert len(observed_writes) == 8
        assert np.allclose(observed_writes, src["write_ns"], rtol=0, atol=1e-10)
        vin = at("vin", start)
        held[(t >= start) & (t < end)] = vin
        decisions, previous = [], 0
        for bit, when in zip(range(7, -1, -1), observed_writes):
            point, captured = when - .02, when + .20
            # 20 ps before write for setup observation, 200 ps after for the
            # native DFF's settled output, before the subsequent update edge.
            assert captured < src["update_ns"][7-bit]
            token, before, trial = [word(prefix, point) for prefix in ("xctrl.t", "d", "xctrl.code")]
            banks = {f"{b}_{r}": word(f"b{b}_{r}", point) for b in ("p", "n") for r in ("h", "l")}
            decision, after = int(at("xctrl.data", point) > level), word("d", captured)
            observed_residual = at("topp", point) - at("topn", point)
            dac = vin - observed_residual
            expected_dac = trial * SPAN_V / 256 - SPAN_V / 2
            assert token == 1 << bit and before == previous
            assert trial == before | token
            assert banks["p_h"] == banks["n_l"] == trial
            assert banks["p_l"] == banks["n_h"] == (255 ^ trial)
            assert np.interp(point, t, valid.astype(float)) == 1
            assert decision == int(observed_residual >= 0)
            assert after == ((before | token) if decision else before)
            assert abs(dac - expected_dac) < 1e-8
            decisions.append(dict(bit=bit, write_ns=float(when), observation_ns=float(point),
                                  capture_observation_ns=float(captured), token=token,
                                  stored_before=before, trial_code=trial, **banks,
                                  decision=decision, stored_after=after,
                                  held_vin_v=vin, dac_observed_v=dac,
                                  residual_observed_mv=observed_residual*1000,
                                  ideal_arithmetic_error_v=dac-expected_dac))
            previous = after
        assert previous == src["word_at_read"] == (145 if number == 1 else 85)
        assert word("d", src["read_time_ns"]) == previous
        assert word("xctrl.t", src["read_time_ns"]) == 0
        frames.append(dict(number=number, sample_end_ns=start, next_sample_ns=end,
                           held_vin_v=vin, final_word=previous, final_binary=f"{previous:08b}",
                           decisions=decisions))
    valid &= np.isfinite(held)
    metrics = dict(case=NAME, scope=case["scope"], context=context,
                   simulator=pinned["simulator"], result_ok=record["ok"],
                   waves_sha256=digest, export_sha256=case["export_sha256"],
                   source_wave_path=f"output/sar8_simple/waves/{NAME}.json",
                   saved_vectors=len(data)-1, all_vectors_finite=True,
                   span_v=SPAN_V, lsb_mv=SPAN_V*1000/256,
                   derivation="DAC = held VIN - (TOPP - TOPN); trial code from actual CODE and P/N controls",
                   display_mask="SAMPLE low; all P/N choices complementary at 10/90% VDD; gaps kept as NaN",
                   digital_display="raw V/VDD, per-bin first/min/max/last; no clipping or averaging",
                   analog_display="raw saved TOPP/TOPN algebraic plant, masked gaps; NOT physical CDAC settling",
                   observations_before_write_ns=.02, observations_after_write_ns=.20,
                   checks_pass=True, new_simulation=False, frames=frames)
    return data, t, supply, frames, held, np.where(valid, held-residual, np.nan), np.where(valid, residual*1000, np.nan), metrics


def lanes(ax, t, data, nets, lo, hi, supply, color, title):
    for offset, (net, label) in zip(range(len(nets)-1, -1, -1), nets):
        x, y = envelope(t, data[net]/supply, lo, hi)
        ax.axhline(offset, color="0.88", lw=.5, zorder=0)
        ax.plot(x, offset + .68*y, color=color, lw=.9)
    ax.set_yticks(np.arange(len(nets))[::-1] + .3, [label for _, label in nets])
    # The 0/1 rails are .68 lane units apart. Full raw excursions are retained.
    subset = (t >= lo) & (t <= hi)
    low = min(float(np.min(data[net][subset]/supply)) for net, _ in nets)
    high = max(float(np.max(data[net][subset]/supply)) for net, _ in nets)
    ax.set_ylim(min(-.18, .68*low-.08), max(len(nets)-.15, len(nets)-1+.68*high+.08))
    ax.set_title(title, loc="left", fontsize=10, pad=7)
    ax.tick_params(axis="y", length=0, labelsize=9)
    ax.spines["left"].set_visible(False)


def analog(ax_dac, ax_res, t, held, dac, residual, lo, hi):
    subset = (t >= lo) & (t <= hi)
    ax_dac.plot(t[subset], dac[subset], color=DAC_COLOR, lw=1.1, label="实际试探 V_DAC")
    ax_dac.plot(t[subset], held[subset], color="0.30", ls="--", lw=1, label="保持的 V_IN")
    ax_dac.set_ylabel("差分电压 (V)", fontsize=9)
    ax_dac.set_title("理想 DAC：试探码 / 写入判决", loc="left", fontsize=10, pad=7)
    ax_dac.legend(loc="lower right", fontsize=8, frameon=False, ncol=2)
    ax_res.plot(t[subset], residual[subset], color=RESIDUAL_COLOR, lw=1.1)
    ax_res.axhline(0, color="0.35", lw=.8)
    ax_res.set_ylabel("残差 (mV)", fontsize=9)
    ax_res.set_title("比较器输入残差 = V_IN − V_DAC", loc="left", fontsize=10, pad=7)
    ax_dac.margins(y=.30)
    ax_res.margins(y=.28)


def decorate(rows, lo, hi, guides, sampling=True):
    for ax in rows:
        ax.set_xlim(lo, hi)
        ax.tick_params(axis="x", labelsize=9)
        ax.grid(axis="x", color="0.87", lw=.5)
        for when in guides:
            ax.axvline(when, color="0.58", ls=":", lw=.55, alpha=.65, zorder=0)
        if sampling:
            for a, b in ((1.01, 41.03), (101.01, 141.03)):
                if max(lo, a) < min(hi, b):
                    ax.axvspan(max(lo, a), min(hi, b), color="0.7", alpha=.12, lw=0)
    rows[-1].set_xlabel("原生仿真时间 (ns)")


def plot_detail(data, t, supply, frames, held, dac, residual):
    fig, axes = plt.subplots(5, 2, figsize=(13.5, 14.5), sharex="col", layout="constrained",
                             gridspec_kw={"height_ratios": [1.6, 3.1, 3.1, 2, 2]})
    fig.suptitle("8 位异步 SAR：位序、暂存码与实际逐次逼近\n原生门级控制器 + 理想采样 / DAC / 比较器测试台", fontsize=14)
    for col, frame in enumerate(frames):
        rows = axes[:, col]
        lo, hi = frame["sample_end_ns"]-1.5, frame["decisions"][-1]["write_ns"]+3.5
        lanes(rows[0], t, data, CLOCKS, lo, hi, supply, "0.28",
              f"第 {col+1} 帧：VIN={frame['held_vin_v']:+.3f} V → {frame['final_binary']} ({frame['final_word']})")
        lanes(rows[1], t, data, [(f"xctrl.t{i}", f"T{i}") for i in range(7, -1, -1)],
              lo, hi, supply, TOKEN_COLOR, "Bit Token：T7 → T0；最后移空即停止回路")
        lanes(rows[2], t, data, [(f"d{i}", f"D{i}") for i in range(7, -1, -1)],
              lo, hi, supply, WORD_COLOR, "SAR word：D7…D0，只保存已经判定的位")
        analog(rows[3], rows[4], t, held, dac, residual, lo, hi)
        for decision in frame["decisions"]:
            when = decision["write_ns"]
            keep = decision["decision"] == 1
            color, marker = ("#298249", "o") if keep else ("#ac4a41", "x")
            rows[3].plot(when, decision["dac_observed_v"], marker=marker, color=color, ms=5)
            rows[3].annotate(f"{decision['trial_code']} / {int(keep)}", (when, decision["dac_observed_v"]),
                             xytext=(0, 10 if decision['bit'] % 2 else 18), textcoords="offset points",
                             ha="center", fontsize=8)
            value = decision["residual_observed_mv"]
            rows[4].plot(when, value, marker=marker, color=color, ms=5)
            rows[4].annotate(f"{value:+.2f}", (when, value), textcoords="offset points",
                             xytext=(0, 9 if value >= 0 else -17), ha="center", fontsize=8)
            rows[0].annotate(f"b{decision['bit']}", (when, 1), xycoords=("data", "axes fraction"),
                             xytext=(0, -12), textcoords="offset points", ha="center", fontsize=8)
        decorate(rows, lo, hi, [d["write_ns"] for d in frame["decisions"]])
    fig.supxlabel("竖虚线：写入沿；数字波形按 V/VDD 分行偏置，保留短暂尖峰。\n模拟曲线空档：参考选择切换；没有模拟真实 CDAC 的电荷保持与建立。", fontsize=10)
    save(fig, "bitwise_approximation")


def plot_overview(data, t, supply, frames, held, dac, residual):
    fig, rows = plt.subplots(5, 1, figsize=(13.5, 13), sharex=True, layout="constrained",
                             gridspec_kw={"height_ratios": [1.6, 3.1, 3.1, 1.7, 1.7]})
    fig.suptitle("两个完整采样周期：8 位 Token + 8 位 SAR word\n原生控制器波形；模拟部分为理想测试台", fontsize=14)
    lanes(rows[0], t, data, CLOCKS, 0, 202, supply, "0.28", "时钟：每个采样周期只转换一次，无第 9 次比较")
    lanes(rows[1], t, data, [(f"xctrl.t{i}", f"T{i}") for i in range(7, -1, -1)],
          0, 202, supply, TOKEN_COLOR, "Bit Token：采样期间初始化为 10000000；转换后全 0")
    lanes(rows[2], t, data, [(f"d{i}", f"D{i}") for i in range(7, -1, -1)],
          0, 202, supply, WORD_COLOR, "SAR word：采样期间清零；转换完成后保持到下一次采样")
    analog(rows[3], rows[4], t, held, dac, residual, 0, 202)
    rows[3].set_title("理想 DAC：逐次逼近保持的输入", loc="left", fontsize=10)
    for frame in frames:
        middle = (frame["decisions"][-1]["write_ns"] + frame["next_sample_ns"])/2
        rows[2].text(middle, 7.8, frame["final_binary"] + f" ({frame['final_word']})",
                     ha="center", va="center", fontsize=10)
    decorate(rows, 0, 202, [])
    for a, b in ((1.01, 41.03), (101.01, 141.03)):
        rows[0].text((a+b)/2, 3.85, "采样 / 初始化", ha="center", fontsize=9)
    fig.supxlabel("灰色：采样相位；1 LSB = 7.03125 mV。模拟空档不是物理 CDAC 波形，未声称真实建立精度。", fontsize=10)
    save(fig, "bitwise_two_cycles")


def main():
    font_setup()
    data, t, supply, frames, held, dac, residual, metrics = extract()
    plot_detail(data, t, supply, frames, held, dac, residual)
    plot_overview(data, t, supply, frames, held, dac, residual)
    target = ROOT / "verification/sar8_simple/bitwise_approximation.json"
    target.write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"checks_pass": True, "wave_sha256": metrics["waves_sha256"],
                      "frames": [{"trials": [d["trial_code"] for d in f["decisions"]],
                                  "decisions": [d["decision"] for d in f["decisions"]],
                                  "final_word": f["final_word"]} for f in frames]}, indent=2))


if __name__ == "__main__":
    main()
