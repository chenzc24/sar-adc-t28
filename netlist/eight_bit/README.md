# Eight-bit deck ownership

The new DUT source of truth is the saved Virtuoso hierarchy, not a hand-fixed
copy of a Spectre netlist. `scripts/eight_bit/build_oa.py` builds the owned OA
cells through supported bridge APIs and exports the unmodified hierarchy to
`output/eight_bit_flat/oa_netlists/<cell>/<tag>/input.scs`.

`run_electrical.py` creates run copies by assigning top-level design variables,
setting numerical options, and adding analysis/save statements. It does not
replace transistors or connectivity in primary comparisons. The comparator
macro's named diode model is supplied as a model definition, not a circuit
replacement. All run decks and raw exports are preserved separately.

The explicitly named `candidate-only` diagnostic omits the old top-level
branch to audit warnings from the native candidate without warning suppression
by the old core bootstrap. It is not the primary matched comparison.

Ideal/noisy clocked VA decks and RC half-circuits are generated independently
by `run_veriloga.py` and `run_electrical.py first-order`, respectively. They
are labeled models, never represented as extracted OA transistor circuits.
Foundry includes and raw OA netlists are not committed to Git. Every accepted
run records its source hash, exact result path and simulator command under
`output/eight_bit_flat/`.
