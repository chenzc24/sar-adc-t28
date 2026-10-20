# SAR8 reference handoff alignment

## Goal and boundaries

Compare a netlist-only aligned reference-gate timing experiment against frozen
R1. Preserve every native transistor/capacitor/resistor, connection and size,
including native controller, StrongARM and Bootstrap. Do not update OA or adopt
the experiment as a new frozen circuit. No push.

Initial git state: branch exp/cdac-flat8-device, HEAD 0b46886; unrelated untracked
cdac10_dualrail config, three VA files, plan, scripts and verification preserved.
Read-only dependencies: all R1 sources/config/results, exact primary OA export,
R1 nfull_fine/nhalf_fine decks and waves, foundry models, all remote OA.

Owned local paths: this plan, plan/log.md (append only), .gitattributes (one new
VA LF-only rule),
models/veriloga/sar8j_aligned_refgate.va,
scripts/integration/reference_alignment.py,
scripts/integration/reference_alignment_analyze.py,
verification/integration/reference_alignment_results.json,
verification/integration/test_reference_alignment.py,
docs/sar8_reference_alignment.md, docs/figures/sar8_reference_alignment/,
ignored output/sar8_reference_alignment/.
Remote OA ownership: none. Simulator owns only unique runner job directories.

## Experiment

Keep the 16 ideal gate boundaries, add a shared ideal timing notification fed
only by the 32 actual native requests. After all requests have remained stable
200 ps and every bank is one-hot, publish a common commit. Changed banks turn
off together and turn on after 100 ps; unchanged banks stay connected. Gate
edges stay 20 ps. Preserve sample-rise 2 ns midpoint restoration and sample-fall
midpoint override. No Vin-based code calculation, no comparator replacement,
no native PHI/CMP clock retiming. This changes the ideal timing boundary only.

## Validation and artifacts

1. Fresh bridge status; use standalone native Spectre SSH (no CIW needed).
2. Derive new immutable decks from R1 fine cases, structural audit all subckts
   except the explicitly changed ideal gate statements in the top. Strip those
   statements and require exact normalized native-top match. Verify R1 hashes.
3. Run TT/.9V/27C, 200ns, APS, maxstep10ps/full solver output; negative-full
   and negative-half first. Same stimuli, loads, models and tolerances as R1.
4. Reuse read-only R1 functional/error/stress analysis, route output to new
   directory; require result.ok, finite saved data, 8 compare/write/update per
   frame, correct code/mapping, compare error <1.7578125mV, no enable overlap,
   BBM >=99.8ps. Report actual CMI/LTE and reference/comparator six-pair peaks.
5. Measure cross-bit gate edges and compare full-rate waveforms, not strobes.
   If useful, add bounded control/positive-full/carry/reversal coverage with
   identical full-rate settings. Retain unsuccessful experiments unchanged.
6. Curate metrics, source/deck/wave hashes and one before/after timing plot.
   No PVT, mismatch, noise, full-code sweep or physical-driver claim.
7. Focused tests, Python compile, visual plot inspection, diff-check, scoped
   log and local commit: test: align SAR8 reference handoff against frozen R1.

## Progress

- Planning: no tracked changes or simulations at start. Bridge v0.8.0 status
  reports tunnel absent, SSH banner resolves thu-wei. No GUI mutation needed.
- Completed two 200ns full-rate native APS cases (no extra scope expansion).
  Both functional/error passes; 32 compare/write/update events across four
  frames. All changed bank on/off threshold spreads zero within saved numeric
  precision; minimum BBM100ps. Native circuitry and frozen R1 hashes match.
- Negative-full conversion reference/comparator peaks .951088/.950686V;
  R1 1.266776/1.250013V. Negative-half reference .951079V, no CMI.
- Negative-full acquisition comparator1.136126V remains at103.173270ns,
  versus R1 1.136124V. This pre-existing separate failure is NOT fixed;
  full nominal qualification remains false. No OA changes/baseline adoption.
