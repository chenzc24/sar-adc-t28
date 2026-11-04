# Complete bit0 BBM: frozen boundary-restoration packages

Local packages only; not registered, submitted or simulated. This restores a
module boundary, not a repair candidate. Parent owns managed FF/SS execution.

## Exact scope

Frozen source: `output/sar8_physical_repair/sar8fix-loaded-ref-ffcold/dut.scs`,
SHA256 `a42e44613b4b1a8a74876a4c996f5bd2bf2e74bf13da6729818ab85bde5a21de`.
The conditional load is the completed `real_l0_v1` pair, not the whole-ADC
performance baseline. No current OA parity is claimed.

- Restore the whole original `XREF.XBBM0`, master `sar8p_nonoverlap`, as local
  `XDUT.XBBM0`: 40 original primitives, including 30 core MOS, six MOM and
  four physical resistors. Both delay legs, clear devices, input inversion,
  AND/NAND stages and their internal MOM loads are copied without resizing.
- Restore original H-driven GNP/GPN ABC chains and X008: 14 core MOS.
  Each H/L output has exactly two driver drains and four actual gate loads;
  no sibling H/L fanout is omitted. L keeps the tested X025 and single IO GPP
  loads; H drives GNP A plus X008, whose output drives GPN A.
- Keep GNN ABC IO, single IO GPP, X025, all 40 Rgate resistors and the existing
  physical CDAC/reference/Bootstrap/reset-comparator load. The other seven
  CDAC bits remain in their previous static states; no other bit is restored.
- The previous two L0SRC MOS are relocated to their original BBM hierarchy,
  not duplicated or resized. All other 142 device records match under explicit
  external-to-internal GNPDRV/GPNDRV node mapping.

`generated/real_bbm_v1/bbm_boundary.json` binds all 40 original BBM primitives,
H/L/Q incident ports and restored H-driver records to parameter hashes.
There are 196 total primitives and 123 MOS. Relative to the prior fixture,
42 core MOS and ten BBM passive primitives are added; the old L0 pair is retained
under its original instance path.

## Ideal boundary and timing

Remove VL0N, VGNP and VGPN. H/L, GNPDRV and GPNDRV are now internal physical
outputs with their real loads; they are not replayed or ideally forced.
CODE represents original `XREF.Q0`, upstream of the complete BBM. Its entire
BBM input load is retained: seven MOS gate ports plus the HD-leg R0 input port.
The original storage/source and its upstream coupling remain outside this
declared ideal CODE boundary.

CODE starts low, rises at 43 ns and falls at 48 ns with 10 ps edges. These
are the old logical event times; no measured H/L edge is aligned back to them.
The former ideal high-reference commands at 44/47 ns are removed. Original
delay legs now determine guard intervals and usable reference ON windows.
External SAMPLE, its sampling window/closing edge, supplies, input/reference
networks, model sections and solver settings are unchanged.

FF=0.99 V/-40 C; SS=0.81 V/-40 C; stop=52 ns. External rails, CODE, SAMPLE
and reset comparator clock are ideal; comparator remains reset. Input and
reference sources retain the previous 50-ohm networks and reference capacitors.
No noise, mismatch or PEX is enabled; this is not a converting ADC test.

## Measurements and failure handling

Each case saves 116 voltages, 656 mandatory currents, 738 six-pair terminal
screens across all 123 MOS, 36 KCL nodes and 376 complete native columns.
Restored core devices retain 0.99 V screens; existing IO retains provisional
1.98 V screens. Preserve raw CMI and all 246 signed junction-polarity/body
observations, including source/receiver interfaces and negative excursions.

Measure actual CODE/H/L and all four reference load-gate edges. Report signed
H/L and per-side off-to-on gaps, sampled H/L overlap, opposed total reference
drain currents and their bias witnesses. Half-VDD crossings and total terminal
currents are diagnostics, not proof of MOS conduction or shoot-through.

Correct ON windows require unambiguous CODE, H/L and actual gate transitions;
the high window ends at the first observed high-reference gate turnoff, with a
declared command-boundary fallback if those off events are missing. Errors are
relative to each side's selected instantaneous VREFP/VREFN. Missing/ambiguous
edges produce unknown windows; observed windows still outside +/-1 mV at their
end remain not established. Neither case is silently accepted at 52 ns.
The prior fixed windows are retained only as labelled legacy diagnostics.

Keep CODE source work separate from VDD work. The CODE load includes resistor
current as well as gate currents. H/L/PRE/GPNPRE source-to-load work and KCL
closure are internal transfers, not additional external power. VDD energy is
grouped by BBM, H driver, X025, GNN ABC IO, GPP IO and physical load.

## Frozen handoff

| Run ID | Recipe relative to this directory | SHA256 | Seven input bytes |
| --- | --- | --- | ---: |
| sar8audit-real-bbm-ffcold | `generated/real_bbm_v1/ffcold/recipe_proposal.json` | `435a572603391889baf830fd51477594e1f40c13b326ad64ea84d89fc7542bd5` | 434235 |
| sar8audit-real-bbm-sscold | `generated/real_bbm_v1/sscold/recipe_proposal.json` | `ebabae8782feee254f667ce04016b900e095d0bac6f9dc309156f5f90b969d33` | 434235 |

DUT SHA256: `5d4318d63e50ef8ea66443cf87f3db44edf16d169d824ab10d7604268194dae4`.
Package receipt SHA256: `e591cdc23af5e27f4e8b308a555ba0e8ba1e175eb69b7a5411a0542f4443a510`.
Resource requests are unchanged: four threads/512 MiB simulation, 256 MiB
analysis, 2 GiB raw output and 30 MiB derived output. Parent serializes runs.

One focused test passed: exact original BBM and H-driver mapping, preserved
conditional devices and complete fanout, no ideal internal forces, unchanged
sampling/external sources, CODE PWL timing, staged hashes and actual-model
limits. A staged analyzer run on synthetic scalar data checks all 738 screens,
source/internal work, BBM energy, current observations and full native columns.
It also checks that missing control edges stay unknown and a bottom voltage
not established by 52 ns stays failed. Synthetic rows are not Spectre results.

Syntax/UTF8/whitespace, no single-incidence internal nodes and all 90 prior
frozen input hash records passed. No remote actions, OA/PDK edits, baseline
adoption, commit or push.
