# Independent mixed-voltage bootstrap experiment

## Goal and boundary

Build and evaluate independently named T28 OA bootstrap sampling experiments
against the existing `sar_bootstrap` baseline. The first candidate replaces
the baseline devices already shown to exceed the core-model warning threshold
with 1.8-V PDK classes; the main signal-following device uses the isolated
1.8-V DNW PCell. This is a screening candidate, **not** a reliability-approved
topology or a claim that a nominal 1.8-V label permits every transient bias.
Do not modify the existing bootstrap, CDAC, comparator, or PDK cells.

At start `main` was 12 commits ahead of `origin/main`, with a clean worktree.
An `exp/bootstrap-protected-eval` branch isolates this experiment. The bridge
`t28_io` tunnel/daemon/Spectre were healthy. Existing unrelated editor windows
were present; none has the new target names. The new target cells did not exist.

## Ownership

- Local owned: this plan; `scripts/characterization/create_bootstrap_protected_eval.py`,
  `scripts/characterization/run_bootstrap_protected_eval.py`,
  `config/bootstrap_protected_eval.yaml`,
  `config/bootstrap_protected_full18_eval.yaml`,
  `docs/bootstrap_protected_eval.md`, exact target entries in
  `virtuoso/cell_manifest.yaml`, `docs/design_log.md`, and `plan/log.md`.
- Generated output: ignored `output/bootstrap_protected_eval/` only.
- Remote OA owned: `SAR_ADC_T28/sar_bootstrap_protected_eval/{schematic,symbol}`
  and `SAR_ADC_T28/tb_sar_bootstrap_protected_eval/schematic`, plus
  `SAR_ADC_T28/sar_bootstrap_protected_full18_eval/{schematic,symbol}` and
  `SAR_ADC_T28/tb_sar_bootstrap_protected_full18_eval/schematic`.
- Read-only: all other remote OA cells, `tsmcN28`, all foundry models and
  documents, baseline OA export/results, and all unrelated local files.

The baseline netlist SHA-256 is
`f3818ef606de602671beac8b6728a1f5460958d03ca0299de0fc79e28132242c`.
Its earlier TT/0.9-V/27-C +0.8-V differential screen had up to 12.026-mV raw
hold error and core-model terminal warnings. The foundry guide describes SOA
warnings but does not provide a checked transient-duration waiver; warning
clearance alone is not lifetime signoff.

## Implementation and validation

1. Read back candidate PDK symbols/CDF and source OA connectivity. Build a
   new DUT and testbench from the established topology. The first candidate
   replaces MN1/MN2/MN3 and MN7/MN13 with `nch_18_mac`, and MN11 with
   `nch_18_dnw_mac`. Its TT screen completed but transferred model warnings
   to core MN5/MP4 and retained -8.97-mV raw error. A separately named
   second candidate additionally replaces MN5/MP4 with `nch_18_mac` and
   `pch_18_mac`. Preserve other devices; use valid 1.8-V geometry.
2. Read back exact D/G/S/B nets, PCell parameters, symbol terminals, and
   check markers. Export the new OA testbench through the bridge and hash the
   unedited Spectre export. Do not hand-edit the exported DUT circuit.
3. Run a bounded TT/0.9-V/27-C differential case at +0.8 V (and any necessary
   additional diagnostic case) with the same phase stimulus and 219.5-fF
   one-side load used in the prior SOA audit. Save all transistor terminal
   nodes, verify Spectre `result.ok`, and calculate six terminal differences
   per device alongside raw held error at 270 ns.
4. Report separately: model-warning pass/fail, acquisition, raw held-error
   pass/fail against 0.439 mV, and reliability-rule status (unverified).
   A failed candidate remains an experiment, not a promoted design. Do not
   expand to PVT or claim reliability completion from this nominal screen.

Require Python compile, OA readback and zero check markers, exact exported
model names/terminals, source-hash association, finite aligned waveforms,
focused Spectre completion, `git diff --check`, and owned-diff review. Record
the outcome in the report/log. Commit locally as
`test: screen mixed-voltage bootstrap prototype`; do not push without request.

## Outcome

Both named candidates were created and read back with zero schematic markers.
Their differential OA exports were simulated directly with Spectre 21.1 at
TT/0.9 V/27 C. The initial candidate had 20 retained `CMI-275x` warnings
(698 further warning instances suppressed) and -8.972-mV raw held error. The
full-control candidate had zero `CMI-275x` warnings and all 144 reconstructed
D/G/S/B metrics below diagnostic levels, but -8.755-mV raw held error.
Both therefore fail promotion; model-warning clearance is not a foundry
transient/lifetime approval. Source hashes, readback, configuration, and
individual result limitations are recorded in `docs/bootstrap_protected_eval.md`.
