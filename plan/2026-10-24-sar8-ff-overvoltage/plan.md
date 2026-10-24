# FF terminal-overvoltage diagnosis on L90 reference candidate

Status: complete (diagnosis and proposals only). Circuit SOA remains unresolved.

## Ownership and frozen inputs

- Candidate e94e802: output/sar8_ref_length/l90_ff_099_{m40,125}_static,
  six 100ns native frames (600ns total), Mmain2um, reference-switch L90,
  W/multi/timing fixed.
- Dirty user Obsidian and untracked10-bit files do not overlap; preserve them.
- Own scripts/sar8_ff_overvoltage/, verification/sar8_ff_overvoltage/,
  output/sar8_ff_overvoltage/, docs/figures/sar8_ff_overvoltage/, this plan and
  plan/log.md. Remote OA ownership none.
- Read-only: candidate sources/native waveforms/logs, all prior experiments,
  PDK and all OA. No baseline replacement, no simulation changes, no push.
- If additional native extraction is required, write only a new diagnostic
  directory /home/chenzc_intern25/TSMC28/llm_IO/sar8_ff_overvoltage_20261024;
  existing native run directories remain read-only. SSH profile t28_io.

## Steps and validation

1. Verify receipts/hashes and native run completion. Inventory every measured
   terminal-pair peak in both corners; distinguish microscopic threshold
   crossings from significant excursions and do not equate pair counts with
   warning occurrences or unique physical causes.
2. Locate representative/worst MOS and trace their four terminals and drivers
   through frozen netlist. Correlate full-resolution stress windows with sample,
   compare/write/update and staged-idle-reset edges. Quantify polarity, peak,
   time and local duration; label window-limited measurements explicitly.
3. Separate directly measured facts from topology-based causal inference.
   Check fixed supply and model SOA limits; no arbitrary warning suppression.
4. Create compact readable waveform figures with limits, actual terminal
   differences, triggering signals, phase annotations and test conditions.
   Visually inspect final plots and verify plotted peaks against native table.
5. Propose prioritized single-variable fixes and regression gates, but do not
   implement. Log results, compile scripts, parse JSON, review scoped diff and
   commit only owned files locally.

Artifacts: inventory and localized event JSON, waveform figures and result
summary in this plan. Raw outputs retained. Intended commit: analyze: localize
FF overvoltage phases and propose bounded circuit fixes.

## Results — measured, not a new simulation

Read only the two frozen native Spectre21.1 CX results. Both native PSF-end
flags and logs confirm completed runs with zero errors; SOA warnings remain.
Verified reduced-artifact receipt, DUT/deck/native hashes. Regenerated no native
run; changed no circuit, PDK, OA, or earlier experiment. The complete DUT has
1833 MOS instances; the existing stress inventory covers445 selected MOS and
2670 terminal pairs per corner, not every transistor. All5340 pair-to-net mappings
match the flattened frozen DUT. Shared nodes cause multiple terminal warnings;
pair counts are not independent events. Native logs also contain devices beyond
this selection and suppress repeat warnings, so the four classes below are not
an exhaustive all-transistor safety certificate.

| Class / representative device (under XDUT) | FF -40C peak / time | FF +125C peak / time | Phase |
| --- | --- | --- | --- |
| XCDAC.XSN4.MN_LOW, Vgb | 1.051037V /172.705835ns | 1.055147V /175.063075ns | Idle reset of bit7, before bit4 reset |
| XREF.XDRV0.GNNCN cold /GPNCN hot, Vds | 1.057553V /65.255969ns | 1.033525V /79.153567ns | Cold: conversion update; hot: idle RST0 |
| XIDLE.XN.MN, Vgs | 1.057117V /54.138314ns | 1.049405V /55.177225ns | Fourth PHI_U pulse, bit4-to-bit3 handoff |
| XCOMP.MNLATP cold /MNLATN hot, abs(Vbs) | 1.045313V /446.938882ns | 1.023285V /143.691624ns | Comparator precharge-to-evaluate |

Durations above0.991V (cold/hot): reference195.7/197.3ps,
driver3.32/3.70ps, ACTIVE10.58/9.56ps, comparator66.14/51.08ps.
The extra1mV is a descriptive duration threshold only, NOT relaxed acceptance.
events.json also stores durations above the actual0.99V limit. Durations use
linear crossings of native samples; all these local intervals are untruncated.
Driver peak neighbor-step averages are0.167/0.169ps, so peaks are represented
by multiple native samples, not fabricated interpolation. Nevertheless a tighter
accuracy/maxstep repeat is needed before finalizing a3ps-spike circuit fix.

VDD is exactly0.99V throughout all eight event windows. The model/native CMI
core limit is0.99V: the high-supply corner has no positive overshoot headroom.
There is no modeled package supply inductance here. The inspected1.8V Bootstrap
terminals do not exceed their1.98V guard. This does not prove all Bootstrap or
all ADC conditions safe, and lowering VDD is not passing the required0.99V test.

### 1. Reference gate: cross-bit disturbance, not its own reset edge

Hot RST7 rises174.762215ns; RST4 does not rise until176.619238ns. At the
175.063075ns peak, Q4 remains low and GNN4 is meant to stay high. BN7 is
0.507439V during its large reset transition, TOPN0.741368V, BN4 disturbed
to0.093582V. GNN4 reaches1.055147V, while GNNDRV4 before the series gate
resistor is only0.991790V. Cold reproduces the same sequence and separation.

Topology plus waveforms support this leading path:
RST7 -> Q7 -> bit7 reference transition -> shared TOPN/CDAC coupling -> BN4
disturbance -> MN_LOW drain-gate coupling -> GNN4 spike. The series gate
resistor weakens fast holding of GNN4. This is a causal hypothesis supported by
timing and node locality, not a completed capacitance/current decomposition.
Other device capacitances may contribute. Extending the delay before RST4 is
not a targeted cure: the disturbance occurs before RST4 already.

### 2. Driver: input-to-output kick before a falling output

Cold GNNB and hot GPNB rise while their final inverter outputs are still high.
The respective outputs first jump above VDD then fall, within a fewps. GNN0/
GPN0 beyond the output resistor barely follow the brief spike. This supports
final-stage feedthrough (including gate-drain capacitance), not a slow high
reference rail. GNNCN/GPNCN are the output NMOS reporting Vds; the shared output
and complementary PMOS must be included in any fix. Exact capacitive current
partition is not measured. Slowing a post-driver reference-switch gate alone
does not necessarily cure the internal driver drain excursion.

### 3. ACTIVE: reporting receiver is not necessarily the source

XIDLE.XN.MN has gate=ACTIVE, drain=IDLE, source/body=0. ACTIVE should remain
high across this conversion update, and it does; it has a short analog spike.
The fourth PHI_U pulse moves the one-hot conversion token from bit4 to bit3.
ACTIVE is generated by XCTRL.X018 (OR reduction of token groups), and also
loads XCTRL.XTIM.X001. The connected driver includes X018.X002.MP0/MP1/MN0.
Existing saves lack A01/A23, AB/BB, token and driver-current waveforms. Thus
the handoff phase and affected net are verified; whether the principal kick
originates in the OR tree or downstream feedback capacitance is not resolved.
Do not attribute generation of the spike to XIDLE.XN.MN merely because it
reports the warning. Add probes before deciding on a topology change.

### 4. Comparator: positive X/Y overshoot at evaluation start

Cold CMP_CLK rises446.925358ns and X peaks13.52ps later. Hot CMP_CLK rises
143.678568ns and Y peaks13.06ps later. X/Y start precharged at0.99V; the
reported negative Vbs is bulk0 minus positive source X/Y, NOT a negative node.
MNLATP source=X and MNLATN source=Y. The same CLK releases MPRSTX/MPRSTY
and enables MNTAIL. Waveforms support clock feedthrough through reset devices
with possible tail/input coupling; they do not isolate each contribution.
This is not idle reference reset and is not solved by reference-switch L90.

## Proposed next experiments — not executed or approved as circuit changes

1. Measurement baseline: short-window stricter accuracy repeat retaining all
   original frames/history, add ACTIVE OR-tree/timing-load nodes and relevant
   branch currents, and expand terminal coverage to all1833 MOS. Do not use
   cold DC initialization at an extracted timestamp as a substitute for history.
   Preserve CX baseline; report actual accuracy settings and peak convergence.
2. Supply contract: keep required FF0.99V as the acceptance test. Optionally
   sweep0.99/0.96/0.93V at otherwise frozen conditions as a headroom diagnostic,
   checking fixed0.9V references and all voltage-domain interfaces. A lower
   regulated core supply or differently rated devices requires an explicit
   specification/architecture decision. Never increase model limits or dismiss
   short-pulse stress without foundry transient-reliability guidance.
3. Reference branch first: separate two variables. (a) In a diagnostic model,
   strengthen only the held-high gate path, leaving commanded transition timing
   unchanged; this tests whether GNN4's weak hold is essential. An ideal holding
   clamp is an attribution experiment, not a transistor implementation. (b)
   Sweep bit7 reset aggressor slew by1x/2x/4x, keeping reset start and sampling
   close unchanged and verifying completion before the next acquisition. If
   effective, implement asymmetric edge-shaping/strong steady-state holding;
   avoid blanket reduction of every gate resistor, which can worsen other kicks.
4. Driver: independently slow/taper the final-stage input edge (first small
   sizing steps0.75x/0.5x upstream drive, not all stages at once). Measure local
   Vds, downstream gate timing, dead time, overlap current and DAC settling.
   Longer reference-switch L already fixes leakage; do not conflate these tasks.
5. ACTIVE: use added probes to select between OR-tree edge balancing/output
   buffering and a conversion-active state held between explicit start/end
   events. A state-latch alternative changes the controller and needs dedicated
   reset/startup/idle verification; it is not justified by one receiver warning.
6. Comparator: independently sweep reset-PMOS width0.75x/0.5x, then compare-clock
   slew1x/2x/4x. If necessary examine separate reset/evaluate controls, including
   reset release's own kick. Check precharge completion, both decision polarities,
   delay, noise/offset implications and kickback. No wholesale1.8V replacement.

Acceptance for a selected implementation: same acquisition closing edge and
window, L90 leakage/Ron benefit preserved, no new reference overlap, full
terminal-limit audit with converged peaks, correct codes/timing including
startup, and all five existing PVT risk points. Full-code/sine regression follows
only after these gates. These proposals do not freeze a new circuit version.

## Artifacts and validation

- scripts/sar8_ff_overvoltage/{inventory,localize,plot,validate}.py.
- verification/sar8_ff_overvoltage/{inventory,events,figures,validation}.json.
- Four native-waveform figures in docs/figures/sar8_ff_overvoltage/:
  01_reference_cross_bit,02_driver_feedthrough,03_active_handoff,
  04_comparator_evaluate. Cold/hot columns use their own local event origins;
  absolute times are shown. No smoothing or synthesized missing signals.
- Inspected all four rendered figures. Plotted peaks equal native peak table;
  verified both polarities, actual transistor connections and timing-edge order.
- Python compile, JSON parse, source/cache/figure hashes, all terminal mappings,
  duration and phase checks pass. Scoped diff reviewed; user Obsidian trailing
  whitespace remains outside scope. Task-only local commit; no push.
