# Reference-switch channel length experiment

Status: complete (experiment complete; ADC NOT qualified). User authorizes L=30/60/90 nm with W, multiplicity and timing
fixed, followed by selected-candidate integrated validation.

## Scope and ownership

- Baseline: commit 288cff7, Mmain=2 um integrated cases in output/sar8_main_width.
- Existing Obsidian edits/deletions and untracked 10-bit experiment are unrelated
  and preserved. No shared dependency overlaps.
- Own scripts/sar8_ref_length/, verification/sar8_ref_length/,
  output/sar8_ref_length/, docs/figures/sar8_ref_length/, this plan and plan/log.md.
- Remote OA ownership: none; no schematic update or baseline promotion.
- Remote experiments: /home/chenzc_intern25/TSMC28/llm_IO/sar8_ref_length_20261024.
- Read-only: all foundry PDKs, existing experiments, frozen DUT/monitor, other OA.
- SSH profile t28_io; native Spectre21.1, CX, 4 threads/job, at most two jobs.

## Steps and gates

1. Check PDK length constraints and grid from available PDK sources; distinguish
   legal model domain, CDF/PCell acceptance and physical signoff. Stop before
   sweep if candidates are outside documented domain. Record provenance/hashes,
   never foundry model contents in Git.
2. Construct immutable exact reference-pair DC probes at FF/.99V/125C for each
   length. Both N and P change L; W/nf/multi and all unrelated circuit parameters
   stay fixed. Measure off current at common measured hot biases and near-zero
   on-state differential resistance with defined body/gate/source biases.
3. Select shortest useful length using leakage/Ron tradeoff. 10 uA/rail is a
   provisional leakage screening target, not a signed-off specification.
4. Insert selected length only in eight reference-switch subcell definitions;
   verify inverse substitution exactly recovers original DUT. Run the existing
   five static PVT risk points (six inputs each) with unchanged timing, W and
   multiplicity. Reuse original length30 results for matched baselines.
5. Require native exit0, immutable source hashes, six frames, correct timing,
   retained sampling aperture, reference-span recovery, code comparison,
   sampling/held errors and terminal-stress/CMI checks. Report failures honestly;
   no noise, mismatch, full-code or FFT qualification in this target.
6. Review compact DC and integrated comparison figures, validate scoped diff,
   log outcome and task-only commit. No push.

## Artifacts

PDK constraints/provenance, preparation/source-inverse checks, native receipts,
DC metrics and selection, integrated reports/comparison JSON, plots, raw native
outputs retained locally or remotely. Existing R3/R4 results remain unchanged.

Intended commit: verify: sweep reference-switch length and screen selected PVT candidate.

## Execution notes

- PDK explicit short-length selector contains 30/60/90 nm for both nch_mac and
  pch_mac. At factor0.9 their scaled geometric lengths are27/54/81nm, within
  matching width/length model bins at existing W150/175nm. These are not Leff
  measurements. Recorded source SHA in verification/sar8_ref_length/legality.json.
  No PCell/DRC assertion: retained OA-derived diffusion/LDE values deliberately
  isolate electrical L; callback/LDE reconciliation remains before OA promotion.
- Initial three DC setups failed SFE-874: extraction copied only first line of
  multiline MOS parameters. Retained failed directories; corrected continuation
  parsing and verified exact full-parameter copies in new *_v2 cases. Native
  v2 runs exit0/PASS, zero CMI; L30 reproduces prior measured-bias pair currents.
- Fixed-bias whole-array load estimates: L30 154.219uA, L60 11.000uA,
  L90 4.052uA. Selected L90 using provisional10uA/rail screen. This does not
  establish that L60 cannot meet ADC accuracy or that L90 is globally optimal.
- Bit7 ON differential Ron N/P: L30 5.197/5.311ohm, L60 6.875/9.100ohm,
  L90 8.585/13.143ohm, central +/-1mV VDS; physical multiplicity384 unchanged.
- Five L90 six-frame integrated PVT cases submitted once; 2concurrent x4threads.
  DUT/deck inverse check proves only16 L fields (8cells,32instantiated MOS)
  changed. Native raw results retained; no OA edits, source-R or clock changes.
- Entire-worktree diff-check finds existing user Obsidian trailing whitespace;
  it is unrelated and intentionally not repaired. Scoped check required at end.

## Final result

L90 is a validated **netlist candidate**, not a promoted OA version. FF hot
settled reference source load at130ns is154.219->5.008uA (96.75% reduction),
reference span884.575->899.494mV. Common-bias DC estimate4.052uA differs from
the integrated5.008uA because the rail/gate biases recover in the full circuit.
Bit2 trialword12 residual at comparison changes-9.410->+4.414mV, restoring
negative full-scale test code10->12 without extra waiting (2.804866->2.804880ns).
Positive test code245->243 also recovers.

| Point | L30 six codes | L90 six codes | Native CMI, L90 |
| --- | --- | --- | --- |
| TT/.90V/27C | 242,12,127,128,127,145 | same | no |
| SS/.81V/-40C | 241,12,127,128,127,145 | same | no |
| SS/.81V/125C | 242,12,127,128,127,145 | 241,12,127,128,127,145 | no |
| FF/.99V/-40C | 243,12,127,128,127,145 | same | yes |
| FF/.99V/125C | 245,10,127,128,127,145 | 243,12,127,128,127,145 | yes |

Expected codes243,12,{127 or128},128,127,145. All25 post-startup frames pass;
27/30 including startup. TT and both SS first frames still fail; SS hot code
gets one code worse. Its actual first-frame preclose error remains~-13.718mV
and held error~-13.491mV: do not infer new acquisition degradation from its
code alone, and do not silently discard first frames.

All30 frame timing/idle checks pass. Maximum candidate conversion41.012ns;
post-startup preclose error<=.146653mV, held error<=.576399mV, versus provisional
1.7578125mV sampling allocation. SS cold frame1 preclose+.0594->+.0600mV;
turn-off waveforms nearly overlap. Same requested clock; sample-close movement
<.00002ps (numerical), acquisition-length movement<.048ps. These are finite
test results, not proof for every code/input or a full dynamic Ron extraction.

FF core stress remains open: original guard .99V; cold failing pairs2008->2008,
hot1727->1740, out of2670 measured pairs. This is a per-pair screen count, NOT
CMI occurrence count. Hot reference peak is1.05515V on XSN4.MN_LOW gate-body at
175.063ns. Native CMI independently exists in both FF logs. Longer L reduces
leakage but does not increase the core device's permitted voltage.

Validation: eight successful native cases (3DC+5integrated), source inverse,
full-parameter Ron copies, KCL, matched effective settings, complete native
frames/stress, independent remote source/artifact hashes and two inspected
figures. DC uses reltol1e-6 with preset_override; integrated baseline/candidate
both effective CX reltol1e-4/maxstep6ns. No equal-accuracy speed claim.
Raw failed/successful cases retained; local generated footprint~.366GiB.
No noise, mismatch, full-code, FFT, PEX or OA callback/DRC validation this round.

Artifacts: verification/sar8_ref_length/{dc_results,selection,integrated_comparison,
validation,remote_receipts}.json; figures length_tradeoff.png and integrated_ff_ss.png.
Task-only local commit; no push and no baseline replacement. Next decisions:
address startup acquisition/reset and FF core voltage margin, reconcile PCell
derived geometry before OA promotion, then broader conversion/mismatch checks.
