# Isolated standard-cell migration onto frozen Mmain2/L90

User asks to merge digital standard-cell replacement independently. Prepare a
separate netlist candidate on byte-frozen historical DUT; do not overwrite the
ongoing TT characterization or adopt an untested baseline. No commit/push.

Owned: this plan, netlist/sar8_l90_mmain2_stdcell_v1/,
scripts/sar8_frozen_static/merge_stdcell.py, management/designs.yaml (new candidate
entry only), plan/log.md append only.
Remote OA objects: none. No remote execution this preparation step. Frozen DUT,
existing control/reference module artifacts, libraries/PDK/OA/history and all
unrelated manual ADC/comparator/Obsidian/10bit work are read-only. Shared dirty
management and module directories are not edited. Existing TT flow continues.

Use existing reviewed standard-cell transformation on the historical source,
not the later full ADC candidate. Preserve all untouched subcircuits exactly;
replace INV/NAND/DFF/clock-buffer implementations and96 ordinary reference
inverter pairs. Retain RC/clear, SR CQB, reference resistors, analog blocks,
Mmain2/L90 and top-level connectivity. Library native transistor internals are
referenced externally only; no copying/modifying foundry contents. Private
capacitors inside removed custom gate implementations leave with those gates.

Validate source hash, exact12 changed masters, unchanged headers/other blocks,
unchanged non-MOS driver statements, invertible text patch and replacement
counts. Record external library identity and generate reference include.
These are structural checks, not simulation/equivalence qualification.

Next validation: same low-code TT stimulus versus original, actual sample
aperture/8-bit handshakes/BBM/stable codes and supply energy; midpoint/endpoints
and SS/FF short tests before complete static/dynamic characterization. Existing
storage FF/SS functional evidence is bounded, not whole-ADC validation.
Overvoltage remains deferred and recorded under current user scope.

Checkpoint: candidate generated SHA f31b66c8fb35003bf7e8ad1a23d9c230b39f1f9651ccc469953e5e52ecf493ea.
Exactly12 master implementations changed;96 reference inverter pairs replaced.
Exact inverse, other-subcircuit/header and driver non-MOS preservation checks pass.
No simulation submitted, no baseline adoption or changes to original finite batch.
