# Transistor Implementations and Candidates

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
