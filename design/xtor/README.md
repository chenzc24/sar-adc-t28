# Transistor Implementations and Candidates

The [single-edge SAR front end](../dut_single_edge.scs) has its own complete DUT entry because
the controller and sampling/preset connections change together. It uses the existing comparator,
sampler, CDAC, reference switches and T28 cell libraries. The eight-bit trial register feeds
the reference directly. Its lowest set bit selects the current trial while ACTIVE is high.
One accepted decision updates the word and clocks the phase flip-flop. The last write holds
the output word and starts the next reference preset. The [native reference decoder](reference/single_edge_d2.scs)
and controller instantiate foundry gates directly, including XOR2, MUX2, clock buffers and
the active-high latch with asynchronous clear.

The falling edge of the tracking clock starts the first delay transition. Each commit then launches the
opposite phase. The comparator stays in reset until that transition arrives and the buffered
comparator outputs have returned to their common precharge state. The first three trials use
eight DEL250 cells and the remaining five use six. The tracking gate drives the controller
sampling input and both bootstraps.

Prepare a standard PVT point with `python -m tools.saradc.single_edge tt REVISION --cell-lpe`. The same
entry accepts `ssc`, `ssh`, `ffc` and `ffh`. Add `--seed SEED` at a cold corner to enable
whole-DUT local mismatch. Use `--restart` at TT for a valid sampling request during conversion.
The cell-LPE runs use TYPICAL at TT, CWORST_T at SS and CBEST_T at FF. Omit
`--cell-lpe` to reproduce the shorter schematic-cell delays. The measurement uses the project's previously extracted DFCNQ
Liberty tables or an explicit `--liberty-tables PATH`. [Front-end verification](../../results/design/sar_single_edge_frontend.md)

Use `python -m tools.saradc.single_edge_lpe ffc 8 6 verify REVISION` to prepare the
fast-cold cell-LPE and extracted-CDAC verification. Use `ssc` for slow cold,
`scan` for the four-frame tap sweep or `boundary` for the 63-to-64 transition.
These tests take the archived stacked CDAC,
its 510 physical terminals and the measured corner gain from the managed run store.
[Physical tap calibration](../../results/design/sar_single_edge_taps.md)

The current ADC pairs `sar=std_delay_qualified` with `timing=std_delay`. Reference uses `minimal_msb_d2`. Sampler, CDAC and comparator use `b`. The previous RC design pairs `sar=reset_data_or` with `timing=quiet8p5`. [Candidate registry](../../specs/candidates.json) · [Measured schematic](../../results/design/sar_std_delay_20261119.json)

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
