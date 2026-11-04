# Thirty paired regeneration samples

Use original B seeds 4101 through 4130 with its 1 µm input devices nominal.
Reuse the six completed cases for 4121/4124. For each remaining seed run
input nominal, input+cross-coupled N nominal, and input+cross-coupled P nominal.
Preserve all other draws, topology, clock, tests and settings. Stop after the
twelfth threshold frame, which includes both guards and all ten bisections.
Validate 89/87/87 rows and all native bounds, preserve invalid samples. Compare
sample SD (ddof=1) of signed held-input thresholds on identical seed sets,
paired-bootstrap SD difference and leave-one-seed-out sensitivity.

Owned paths are this plan, append-only plan/log.md, new scripts/sar8_mc/regen30,
verification/sar8_mc/regen30, output/sar8_mc/regen30, sar8rg30-* recipes/runs
and their new remote SSD campaign. Prior results, frozen netlists, PDK, OA,
other automations read-only. 1264 initial git status lines with unrelated work.
Four concurrent managed slots, existing simulation and analysis caps.
Deliver per-seed thresholds, validity and warning receipts, aggregate report.
No OA operations or commit/push.

2026-11-04 — Completed 30 paired seeds (4101–4130), 84 new managed runs plus 6 reused. All threshold brackets valid and row checks matched. Sample SD in mV: input nominal 5.027, additionally N nominal 1.714, additionally P nominal 4.005. Paired SD gap 2.291 mV, bootstrap95 [1.144,3.378], leave-one-out [1.733,2.413]. Prioritize MNLATN/P for remaining mismatch under this TT fixture. A read-only fetch interruption was recovered; original simulations retained. Report verification/sar8_mc/regen30/README.md. No design adoption, OA edits, commit or push.
