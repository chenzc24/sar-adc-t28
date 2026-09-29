# StrongARM input-pair scaling iteration

## Goal and ownership

Measure whether enlarging only the T28 StrongARM input differential pair
improves near-threshold transient-noise and local-mismatch behavior enough to
justify a subsequent full-CDAC candidate. Keep the existing 11-MOS baseline
and all user windows untouched. This is a bounded sensitivity experiment,
not comparator acceptance.

Starting Git state: clean `main`, 12 commits ahead of `origin/main`. The
previous exact-CDAC integration showed nominal ±0.439-mV decisions in
224 ps, 0.374-mV peak top-plate kickback, and existing bootstrap SOA warnings.
Standalone StrongARM screens estimated effective input noise around
0.702 mV and found 27/32 paired mismatch samples outside the provisional
±0.439-mV bracket. The larger input pair may alter speed, kickback, and
input capacitance; width alone is not assumed to solve all budgets.

Owned local paths: this plan, new
`config/strongarm_input_pair_scaling.yaml`, new
`scripts/characterization/create_strongarm_input_pair_scaling.py`, new
`scripts/characterization/run_strongarm_input_pair_scaling.py`, new
`docs/strongarm_input_pair_scaling.md`, and bounded entries in
`virtuoso/cell_manifest.yaml` and `plan/log.md`. Ignored generated artifacts
go under `output/strongarm_input_pair_scaling/`.

Owned remote OA objects: new only
`SAR_ADC_T28/sar_strongarm_t28_f2/{schematic,symbol}`,
`SAR_ADC_T28/tb_sar_strongarm_t28_f2/schematic`,
`SAR_ADC_T28/sar_strongarm_t28_f4/{schematic,symbol}`, and
`SAR_ADC_T28/tb_sar_strongarm_t28_f4/schematic`. Read-only dependencies:
`SAR_ADC_T28/sar_strongarm_t28/{schematic,symbol}` and
`tb_sar_strongarm_t28/schematic`, prior exports and reports, all other OA
cells, PDK `tsmcN28`, and user-owned windows. No shared library or existing
cellview writes.

## Method and gates

1. Preflight Git state, Bridge 0.8.0+ `t28_io`, tunnel/daemon/Spectre,
   CIW/windows, exact library mapping/technology, baseline readback/markers,
   and absence of all new target cellviews. Stop on lock, modal/unsaved
   target, incompatible mapping, or unexpected existing target.
2. Reuse the proven 11-MOS StrongARM schematic/symbol and independent
   standalone testbench construction. Change only `MNINP/MNINN` fingers
   from 1 to 2 or 4 at `Wfg=1u`, `L=30n`; preserve every other device and
   topology. Read back PDK masters, terminals, sizing, symbols and zero
   markers. Export the exact OA testbench netlist and verify that the
   candidate DUT differs from the baseline only in the intended pair
   instance finger parameters.
3. Run noise-free TT/0.9-V/27-C ±0.439453-mV decisions and a compact
   transient-noise/paired local-MC screen under the *same* model sections,
   seed, clock, supply and 5-fF output loads as the baseline. Use a bounded
   sample count for sensitivity, not yield. If a candidate improves both,
   optionally use the existing full-CDAC interface as a read-only reference
   and propose the next integrated test; do not rewrite its OA testbench or
   claim ADC acceptance.
4. Preserve exported decks, Spectre logs, PSF and raw data. Report decision
   polarity/time, noise wrong counts with uncertainty, local-MC bracket
   counts/validity, model warnings and input-capacitance/kickback limitations.
   Validate Python/YAML, OA readback and hashes, Spectre result status, PSF
   coverage and `git diff --check`. Commit only owned files as
   `test: screen StrongARM input-pair scaling`; do not push without request.

## Outcome

Both independent candidates were created and read back with 11 T28 devices,
eight testbench instances, and zero markers. The exact exports verified
that only `MNINP/MNINN` finger-related geometry changed. TT nominal delays
improved from the baseline 223.35 ps to 161.53 ps (f2) and 133.73 ps (f4).
At ±0.439453 mV and the common noise seed, the first-48-per-sign wrong
counts were 23/96 for the saved baseline subset, 24/96 for f2, and 17/96
for f4. Valid 16-draw local-MC paired brackets contained 1/16 (f2) and
0/16 (f4), versus 3/16 in the first 16 of the saved baseline run. Neither
candidate is accepted, so the full-CDAC bench remains on the original DUT.
The mismatch source and larger input capacitance remain open. Exact evidence,
sample-size caveats and next diagnostic direction are in
`docs/strongarm_input_pair_scaling.md`.

During result recording, a concurrent bootstrap experiment switched the
original shared checkout to `exp/bootstrap-protected-eval` and edited the
same log and manifest. Its commit was allowed to finish untouched. This
StrongARM target was then moved to the separate
`E:/bridge-Agent-T28/worktrees/sar-adc-strongarm-input-pair-scaling`
worktree, branched from local `main` at `91f2a6c`. Its exact generated
results and a read-only copy of the baseline export were also moved/copied
under this worktree's ignored `output/`. The bootstrap branch and its files
are not staged or altered here. This target's log/manifest entries and
commit are now owned only in the isolated worktree.
