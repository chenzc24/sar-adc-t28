# Locate bottom-plate undershoot in complementary reference switching

Status: complete. Diagnosis and modification proposal only; no fix implemented.

## Scope and ownership

Read frozen 0e495c0 symmetric-hold/native ADC evidence, FF0.99V cold/hot,
Mmain2um/referenceL90nm. Identify low-to-high bottom handoff, individual MOS
branches and gate timing. Do not implement a fix or alter sampling sources.
Own this plan, plan/log.md, scripts/sar8_bottom_undershoot/,
verification/sar8_bottom_undershoot/, output/sar8_bottom_undershoot/,
docs/sar8_bottom_undershoot.md, docs/figures/sar8_bottom_undershoot/.
Remote OA ownership:none. PDK/OA, all prior experiments and scripts read-only.
Preserve dirty Obsidian and10-bit experiment changes. No push.

## Steps and validation

1. Verify native source/provenance hashes and flatten branch mapping. Inspect
   saved native-point neighborhoods: cold conversion BP7 minimum; cold/hot
   idle BN7 minima. Compare corresponding baseline cases if available.
2. Align bottom, actual VREFN/VREFP, low-NMOS gate, high-PMOS gate, top plate,
   controller/reset signals and keeper enables. Quantify onset, gate thresholds,
   peak, recovery and reference-vs-local voltage separation. Gate thresholds
   are timing markers, not assumed physical MOS threshold voltages.
3. Separate measurements from inference: voltage timing alone cannot assign
   exact Cgd/channel-charge/current percentages. Existing current probe coverage
   must be inspected; no claim of transistor-resolved KCL without saved currents.
4. Produce bounded waveform figures and modification experiments in priority
   order, preserving sample opening/closing and non-overlap safety. No circuit
   implementation without subsequent user request. If new diagnostic probes
   are essential, extend this plan before any unique netlist-only run.
5. Validate cache hashes, terminal equations, source mapping and numeric event
   summaries; visually inspect figures, compile and scoped diff. Record limits
   and findings, then task-only local commit. Native arrays never overwritten.

Intended commit: analyze: locate reference bottom undershoot during handoff.

## Review and results

- Reused four native null/symmetric FF runs, eight selected event windows;
  verified DUT/deck/reduced-source hashes and flattened drain/gate/source/bulk.
  No simulations, remote operations, OA changes or source-waveform overwrites.
- Low-to-high reference handoff identified: idle XSN7 BN7, conversion XSP7 BP7.
  Low-N gate fall precedes high-P gate fall and two negative excursions. Cold
  idle -31.68mV before high-P gate fall -> -56.68mV peak at472.660ns, while
  VREFN=-3.67mV. Hot idle -41.70mV at275.206ns, VREFN=-5.96mV.
- Conversion repeats same sequence, BP7 -56.74/-44.95mV cold/hot. No subsequent
  bit full gate transitions or active sample edge during selected undershoot.
  Complementary bottom switching/reference/array feedback remain possible.
- Branch currents not saved; capacitance/channel-charge split unproven. Gate
  99% markers are not physical Vth or proof of zero channel current. Voltage
  subtraction not causal percentage. No SOA or complete-circuit pass claim.
- Proposed current probes/accuracy convergence, low-N slew, independent high-P
  advance, then reference-R diagnostic. Require overlap current, settling,
  sampling invariance and terminal-stress checks before promoting any fix.
- Compiled all3 scripts; extraction executed and8-event focused validation
  passed. Inspected both final figures, revised stage labels to avoid legend
  overlap. Report distinguishes native circuit from ideal idle holds, includes
  unequal idle event inputs and effective CX settings. Scoped diff reviewed.
- Task-only local commit; no push. User Obsidian/10-bit changes untouched.
  Scoped staged diff-check passes. Whole-worktree diff-check reports existing
  trailing whitespace in user-owned Obsidian Report/Wrap-up & Experience.md:13;
  deliberately not changed or staged.
