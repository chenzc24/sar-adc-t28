# Restore the original L0 output stage

Frozen local FF/SS packages only; not registered, submitted or simulated.
Parent owns managed execution. Conditional baseline is the completed GPP
single-IO pair, not the original whole ADC performance baseline.

## Exact boundary and complete load

Original source: `output/sar8_physical_repair/sar8fix-loaded-ref-ffcold/dut.scs`,
SHA256 `a42e44613b4b1a8a74876a4c996f5bd2bf2e74bf13da6729818ab85bde5a21de`.

- Restore `XDUT.XREF.XBBM0.X004.X001`, master `sar8p_inv`, as local
  `XDUT.L0SRC`. Full original core parameters retained: N W=500 nm,
  P W=1 µm, L=30 nm, nf=1, multi=1.
- Its original output `XDUT.XREF.L0` has exactly six incident ports:
  this driver's two drains, X025 MN/MP gates, and original GPPAN/GPPAP gates.
  The conditional baseline has already replaced the latter GPP block with
  GPPIN/GPPIP. Both new IO gates and both X025 gates are retained as actual
  loads. There are no additional sibling L0 loads to slice or omit.
- Local output is `XDUT.L0`; all 142 existing device records remain identical
  under this one explicit L0 internal-node rename. Add only the original two
  driver MOS. X025, GPP IO geometry, ABC, Rgate and physical loads are unchanged.
- Move the ideal source to `L0N`, representing original
  `XDUT.XREF.XBBM0.X004.N`. This is the preceding NAND `X004.X000` output.
  Its original incidence is three NAND drain ports plus the restored inverter's
  two gates. The NAND and upstream BBM are omitted at this declared ideal
  boundary; this is not full BBM validation.

`generated/real_l0_v1/l0_boundary.json` records the original instance/port lists
and parameter hashes. No other physical load is silently replaced.

## Stimulus and measurements

L0N starts low, rises at 43 ns and falls at 48 ns, with the same 10 ps edge
width and command midpoints. It is the logical complement of the previous
ideal L0 command. There is no delay compensation or internal edge alignment.
L0/PRE/GNN/GPP timing now emerges from the added inverter and actual load.
All other external sources, sampling window/closing edge, model sections and
solver settings are unchanged. FF=0.99 V/-40 C; SS=0.81 V/-40 C; stop=52 ns.

Each case measures 95 voltages, 470 mandatory currents, 486 terminal-pair
screens across 81 MOS, 13 KCL nodes and 142 full native columns. Added L0SRC
and existing X025 remain screened at 0.99 V; prior IO screens remain 1.98 V.
Retain all new driver D/G/S/B currents, 162 junction-polarity observations,
negative excursions, actual N-to-L0/branch delays, same-side control gaps and
correct ON settling. Missing/extra edges remain unknown, not accepted.

Keep ideal N source work separate from VDD work. L0 output-to-gate work and
PRE transfer are internal exchanges, with explicit closure residuals; neither
is an additional external supply. The previous ideal-source L0 work field
names are retained for comparison, but now refer to the physical driver's
internal output work. This test does not establish ADC power or lifetime safety.

## Frozen handoff

| Run ID | Recipe relative to this directory | SHA256 | Seven input bytes |
| --- | --- | --- | ---: |
| sar8audit-real-l0-ffcold | `generated/real_l0_v1/ffcold/recipe_proposal.json` | `9ca350694455bfbe7d05f0daef82399daf42dbc0d967558f738354a1396258c7` | 303812 |
| sar8audit-real-l0-sscold | `generated/real_l0_v1/sscold/recipe_proposal.json` | `84057714e091d28f1d08ccf0c6eab515cb93f264a751367bfd310dbc24475202` | 303812 |

DUT SHA256: `0981e346395c38d73487dc9b6b1523ed12f4d15af6681d47a0e986e953db9422`.
Package receipt SHA256: `d7127ef7bc495c1d5eacecf050f6c644f65ed70ea18bdc476d4df0835e9c3944`.

One focused test passed: original-driver mapping, complete fanout, all retained
records, external source invariance, complementary PWL with unchanged times,
input hashes, new core screen rejection, and staged analyzer execution on
synthetic scalar rows. It covers new driver stress/body/current observations,
N source/internal work closure, emerged positive delay, negative L0 and proper
ON settling. Synthetic rows verify measurement plumbing, not circuit behavior.

Syntax/UTF8/whitespace, no single-incidence internal nodes, and all 76 preceding
frozen input hash records passed. No OA/PDK edits, baseline adoption, commit,
push or new simulation.
