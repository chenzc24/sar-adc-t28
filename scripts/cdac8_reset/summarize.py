"""Compact deterministic evidence ledger and nominal-hierarchy correlation."""
from __future__ import annotations

import numpy as np
from support import OUT, dump, load


def wave(category, name):
    result = load(f"{category}/{name}_result.json")
    assert result["ok"]
    return {k: np.asarray(v) for k, v in load(f"{category}/{name}_waveform.json").items() if k != "units"}


def correlation(left, right):
    a, b = wave(*left), wave(*right)
    grid = np.linspace(100e-9, 289e-9, 18901)
    delta = np.interp(grid, a["time"], a["topp"]-a["topn"]) - np.interp(grid, b["time"], b["topp"]-b["topn"])
    return float(np.max(np.abs(delta))*1000)


def main():
    categories = ("screen", "extra", "ab", "joint", "nominal", "integration")
    expected = dict(zip(categories, (11, 3, 1, 3, 3, 3), strict=True))
    rows = []
    for category in categories:
        current = load(f"summary_{category}.json")
        assert len(current) == expected[category], (category, len(current))
        assert all(r["result_ok"] and r["code_pass"] for r in current)
        assert all(r["reset_error_at_98ns_mv"] < 1 for r in current)
        rows += current
    correlations = {
        "diagnostic_to_exact_oa_max_common_grid_mv": correlation(("screen", "screen_pfast4"), ("nominal", "oa_nominal")),
        "aggregated_to_literal_loop_max_common_grid_mv": correlation(("nominal", "oa_nominal"), ("integration", "oa_literal")),
        "aggregated_to_literal_fixed128_max_common_grid_mv": correlation(("nominal", "oa_fixed128"), ("integration", "oa_literal_fixed128")),
        "scope": "nominal deterministic checked trajectories only, not PVT or MC equivalence",
    }
    assert all(value < .001 for value in correlations.values() if isinstance(value, float)), correlations
    result = {
        "successful_native_aps_runs": len(rows), "diagnostic_runs": 18, "exact_oa_runs": 6,
        "case_count_by_category": expected, "all_checked_codes_correct": True,
        "all_checked_reset_final_levels_within_1mv": True,
        "max_reset_final_error_mv": max(r["reset_error_at_98ns_mv"] for r in rows),
        "nominal_correlations": correlations,
        "candidate_qualified": False, "reason": "cross_input_reset_stress_still_fails_at_TT",
        "broad_pvt_not_run": "known TT cross-input gate failure; no candidate promoted",
        "bootstrap_acquisition": "unchanged_and_explicitly_deferred",
    }
    dump("summary.json", result)
    print(result)


if __name__ == "__main__":
    main()
