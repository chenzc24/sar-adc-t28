# Eight-bit two-rail, complementary common-mode-preserving CDAC candidate

## Goal and scope

User corrected the resolution: the Canvas sketch is only topology reference;
the requested design remains EIGHT bit. User asks to proceed and review when
done. Preserve old eight-bit baseline and independent superseded 10-bit work.
Implement two references without a bottom VCM branch, retaining the existing
128:64:32:16:8:4:2:1 plus dummy array (256 physical 4.004-fF units per side,
1.02504 pF). In response to the user's 01111111/common-mode concern, select
complementary P/N switching, not strict one-sided downward monotonic switching.
State this distinction explicitly in the report and Canvas.

Reference sketch: original Canvas CDAC/dut revision 266, unchanged. Owned
unfinished Canvas review Cells from the superseded target may be renamed and
adapted; remove only our unreviewed 256-Cu pair and four associated switches.
Do not edit the user's original diagram or change its top-Cell designation.

## Dirty state / ownership

Branch exp/cdac-flat8-device. Owned superseded cdac10_dualrail untracked paths
are unrelated history; preserve and exclude from this target's commit. Concurrent
untracked plan/2026-10-20-sar8-async-implementation and scripts/sar8_async are
read-only, do not stage or revert. The concurrent models/behavioral/sar_async.py,
models/veriloga/sar8a_*.va, config/sar8_async_impl.yaml and
verification/sar8_async are also read-only.
Do not edit the concurrently updated README/async architecture. This target's
fixed-period controller is a CDAC characterization fixture, not a replacement
of the selected asynchronous SAR architecture. Own this plan; config/cdac8_dualrail.yaml;
models/veriloga/cdac8_dualrail_*.va; scripts/cdac8_dualrail/;
verification/cdac8_dualrail/; docs/cdac8_dualrail.md;
docs/figures/cdac8_dualrail/; bounded plan/log.md append. Evidence under ignored
output/cdac8_dualrail/. Scoped local commit, no push.

Remote owned SAR_ADC_T28: cdac8_dr_sw_b0..b7, cdac8_dr_nominal,
cdac8_dr_literal (schematic/symbol), cdac8_dualrail_controller,
cdac8_dualrail_input, cdac8_dualrail_comparator (symbol/veriloga only),
tb_cdac8_dr_nominal, tb_cdac8_dr_literal, tb_cdac8_dr_strongarm,
tb_cdac8_dr_ideal_sample (schematic). Refuse existing objects/unsaved targets.
Old Bootstrap, StrongARM, cdac8_unit and cdac8_bank_1..128 are read-only; verify
fresh dependency equality and exact technology/library path before mutation.

## Algorithm, timing and pass criteria

VDD/VREFP=.9 V, VREFN=0, 10 MS/s, input common-mode .45 V, span +/- .9 V.
Dummy P stays high, dummy N stays low. Sampling state uses active code 128:
P-high vector 01111111, N-high vector 10000000, low controls complementary.
Each side's mean bottom reference is .45 V. First MSB trial equals this initial
state; first comparison is the acquired input. Every later tentative trial
sets P-high=NOT(code), N-high=code with bank-local break-before-make. Ideal
VTOPP+VTOPN stays .9 V, although finite edges, delay mismatch, rail impedance
and parasitics can disturb it. No promise of transistor-level CM perfection.
This is binary/complementary SAR, not strict monotonic capacitor switching.

Keep original Bootstrap topology, sizing, 1.05..41.05-ns sample pulse and
5-ns compare period. First comparison 46.01 ns; eight latches finish 82.51 ns.
Restore code128 in the NEXT sampling phase at 3.01 ns of the next cycle,
about 2 ns after Bootstrap reopens. Do not restore a floating top node merely
because it is a two-rail array. Control/clock/ideal comparator are declared VA;
reference MOS/drivers and MOM capacitors are native T28. Actual unchanged
StrongARM is a separately reported interface test, not a qualified 8-bit ADC.

LSB=7.03125 mV; deterministic gate .25 LSB=1.7578125 mV. Reference/driver
16 banks x 8 MOS = 128 native MOS. Screen every Vds/Vgs/Vgd/Vbs/Vbd
against .99 V for this .9-V core fixture, preserving CMI and suppressed counts;
not foundry reliability signoff. Static center tests do not prove DNL/INL.
Unchanged Bootstrap cold-SS and comparator noise/mismatch limitations persist.

## Work and validation

1. Fresh preflight/dependency readbacks; 256-code ideal charge oracle and
   ideal CM proof. All OA built only through bridge; no PDK edits/uploads.
2. Build native leaf switches, nominal/literal arrays (512 independent units),
   benches and VA controls. Require zero markers and exact native exports.
3. APS smoke, +/-input, ideal sampler/native sampler, nominal/literal, actual
   StrongARM comparison; then bounded static/coherent-sine and corner checks
   as warranted. Preserve sources/VA/deck hashes and all failure results.
4. Adapt and wire Canvas overview and 8-MOS expansion, verify expected logical
   topology and native sizes, render/inspect/export, leave 8-bit review visible.
   Switch glyphs in overview are explicitly MOS-path abstractions. No T28 PDK
   model body is embedded; Canvas is review, Spectre is the simulation evidence.
5. Targeted tests, dependency audit, report/plots with ideal baselines and
   sample/convert/reset windows; git diff --check, scoped log/commit.

## Validation gate revision after native TT failure

The -0.8-V completed native case exposes BP6 about 1.231 V at 47.63 ns,
well beyond the .99-V reference-core screen, during SAR redistribution rather
than next-sample restore. This is a hard failure even if output codes are right.
Retain the candidate for user review, not baseline promotion. Stop only the two
owned long static/sine Spectre processes after exact PID/owner/command checks;
retain their logs/partial PSF and status as interrupted/incomplete. No complete
256-code native static/FFT or PVT qualification is claimed. Three pure ideal
oracle checks remain separate from native evidence. Finish all completed
short-case analyses, wiring, failure plot, readbacks and scoped report/commit.

## Final outcome

Completed the bounded candidate and failure diagnosis, not the electrical
qualification. Eighteen result.ok native APS runs total (five initial-version
checks, thirteen final-version cases); two long cases intentionally interrupted
at 8.08253/7.95263 us after the hard failure, raw records retained. All nine
final held-input code checks correct and compare residual error <=.358645 mV;
all nine reference-core screens fail. Global worst 1.399620 V at 203.128786 ns,
XCDAC.XSN5.MN_LOW Vbd, -0.5-LSB input, 127->128 restore inside sampling.
Separate -0.8-V SAR spike 1.231041 V at 47.628927 ns. No baseline promotion,
no complete native static/FFT, PVT/noise/MC/layout or async-controller claim.

Fourteen saved OA schematics have zero markers, final exports identical to
the simulated DUTs, three VA remote/local hashes equal, twelve read-only
dependencies unchanged. Literal hierarchy counts 512 independent MOM units.
Canvas review/leaf revisions 24/27: zero errors/warnings, expected topology
equal; original dut stays revision266. Eight focused Python evidence/oracle
checks pass; scripts compile; five images visually inspected. Curated report
docs/cdac8_dualrail.md and small metrics/figures, raw output/cdac8_dualrail/.
Scoped local commit only; unrelated 10-bit history and concurrent async work
remain unstaged. Stop here for human review of switching and recovery strategy.
