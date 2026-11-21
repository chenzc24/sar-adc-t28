# Transistor Implementations and Candidates

The current ADC uses `sar=single_edge` and `reference=single_edge_d2`. Sampler, CDAC and comparator use `b`. Since 2026-11-21 the sampler `b` has four parallel 1 µm main switches instead of two. [Candidate registry](../../specs/candidates.json) · [Adoption report](../../results/design/sar_single_edge_adoption_20261120.md) · [Sampler main-switch adoption](../../results/design/sampler_mmain4_adoption_20261121.md)

## Single-edge SAR

The [SAR](sar/single_edge.scs) and the [native reference decoder](reference/single_edge_d2.scs) instantiate foundry gates directly, including XOR2, MUX2, clock buffers and the active-high latch with asynchronous clear. The eight-bit trial register feeds the reference directly, and its lowest set bit marks the current trial. COMMIT is the only register clock. The next trial word is precomputed, and the eighth commit registers DONE, which asserts the reference preset.

After each commit, the comparator stays in reset until the delay transition reaches the selected tap and the buffered comparator outputs have returned to precharge. The taps are 11, 9, 7, 6, 5 and 4 DEL250 stages for bits 6, 5, 4, 3 and 2–0. Five sticky registers select them. Each is set by the commit before the tap is first used and cleared by sampling, so a tap only becomes shorter within a frame. Tracking precharges every tap high. The first comparison therefore waits only for the bootstrap gates to turn off, through two DEL250 cells and an AN2 qualifier. A two-flop Johnson counter supplies the phase, PHASE = PHA XOR PHB.

Three choices keep internal nodes within the terminal-voltage rule:

- The write AND has VALID on its inner input.
- The sticky-select ORs and the reference MSB OR use INV+INV+ND2.
- The phase register is the two-flop counter.

## Simulation entries

Use `python -m tools.saradc.single_edge_lpe CORNER KIND --cdac nominal|cworst --revision REVISION` for foundry cell LPE with the extracted CDAC and its 510 physical terminals. KIND is one of:

- `verify`: eight frames;
- `scan`: 255, 0, 85, 170;
- `boundary`: 63/64 at gain-adjusted centres;
- `extreme`: full-scale and low-to-mid steps;
- `restart`: an accepted sample during conversion.

Add `--taps 11,9,7,6,5,4` to override the chain, `--seed SEED` at a cold corner for whole-DUT local mismatch, or `--bootstrap PHYSICAL_ID` to replace both Bootstrap channels with a verified core extraction. The CWORST_T CDAC exists for the cold corners only. The cell-LPE library is TYPICAL at TT, CWORST_T at SS and CBEST_T at FF.

`python -m tools.saradc.single_edge CORNER REVISION [--cell-lpe] [--seed SEED] [--restart]` runs the schematic CDAC. Both entries use the adopted 45 ns high phase from `specs/arch.json`.

## Candidates

Place a new candidate in `design/xtor/<module>/<name>.scs` or a same-named subdirectory. Retain the existing implementation. Provide all definitions needed by the module and preserve its registered public master and port order. Internal structure may vary. The testbench supplies platform includes, the PDK, and standard cells.

```powershell
python -m tools.saradc candidates list
python -m tools.saradc candidates add --module comparator --id trial --file design/xtor/comparator/trial.scs
python -m tools.saradc block sim --module comparator --candidate comparator=trial --run-id NEW_ID
python -m tools.saradc sim tt_short --candidate comparator=trial --run-id ANOTHER_NEW_ID
```

Registration leaves the active selection in the registry. A per-run `--candidate module=name` changes the generated package and records the candidate ID, file, and digest in the receipt. Packaging checks interfaces, duplicate definitions, undeclared dependencies, and argument counts. Use actual tests for function and performance.

Adopt a candidate through an explicit design change. Update the default selection, canonical design entry, and implementation manifest, then verify affected modules and the ADC interface. Qualify each run against its own inputs. Use `--view frozen-b` for the historical B regression.

Candidate adoption is manual. Native simulation uses the existing managed queue. [Standalone tests](../../tb/blocks/README.md) · [Results](../../results/README.md)
