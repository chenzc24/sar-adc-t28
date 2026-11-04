# Regenerative-pair mismatch isolation

Use the frozen B physical hold fixture with the input pair nominal. For each of
4121 and 4124, nominalize only MNLATN/P or MPLATN/P in addition. Measure the
signed held threshold against the existing input-pair-nominal control. Require
the other 87 native rows to match the parent exactly, the selected devices to
be excluded, a valid native decision bracket, and hash-checked collection.

Own this plan, append plan/log.md, the followups generator/runner, new regen
manifest, sar8phys-*-regen* recipes/runs/fixtures and results, and regen report
in verification/sar8_mc/physical_input. Existing sources, OA, PDK and prior
results read-only. Familiar dirty tree (1255 status lines) outside the new
case IDs. No OA objects. Use managed execution and original resource caps.
No commit or push.

2026-11-04 — Four paired native runs completed, with valid held thresholds and exact 87-row mapping. NMOS/PMOS signed influences (baseline minus disabled) in mV: seed4121 -4.873/-2.624, seed4124 +2.124/+2.499. No common dominant branch across these samples. See verification/sar8_mc/physical_input/regen.md.
