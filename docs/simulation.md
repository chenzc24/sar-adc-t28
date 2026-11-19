# Simulation and Monitoring

At experiment closeout, before submitting a large batch, or when reclaiming disk space, archive the evidence needed for measurements and figures. Use the retention checklist to release eligible raw waveforms. The current managed executor leaves deletion to the checklist. [Waveform Retention and Cleanup](waveform-retention.md)

Prepare the 45-point extension with `python -m tools.saradc.pvt_short --revision NEW_ID`. It uses `specs/pvt_short.json` to exclude the original five and freeze the other 40 corners for the current OR design. Each corner uses ten code centers, a 1.059 µs duration, a 10 ps maximum step, four threads, and a 4 GiB output budget. The saved signals cover the actual interfaces and timing measurements. Use the all-terminal flow for a device-by-device terminal-voltage verdict. The references are fixed at 0 V and 0.9 V, passive models use TT, and the setup has a single supply domain with no separate 1.8 V rail.

`tools/saradc/managed/batch_follow.py` schedules a finite batch on the server. It reads registered run IDs and recipe hashes, uses managed admission, simulation, and analysis, and starts analysis automatically. Each batch has one controller lock. It retains failures and uncertain results for review and continues other corners. Use the retention policy after collecting and archiving the complete results.

Use `python -m tools.saradc behav generate` to synchronize Verilog-A and Python behavioral views with the specification. Use `behav check` for numerical cross-checks, `behav sim --run-id sar8-modules-v3` for native module and mixed-hierarchy verification, and `behav follow --run-id ID` to wait once, analyze, and collect. Review failures before rerunning. Registered IDs bind frozen inputs. Assign a new ID after changing the source. [Behavioral models](../design/behav/README.md)

Run `.venv/Scripts/python.exe -m tools.saradc` from the project root. The managed executor uses unique run identities, frozen inputs, resource queues, independent analysis, and digest-verified collection.

For the current minimal reference, use the dedicated short test with its own event counts.

```powershell
.venv/Scripts/python.exe -m tools.saradc.reference_short prepare --version current --corner tt --revision current-v1
```

The following commands are for frozen-B regression. General `prepare` packages the selected view. The legacy analyzer uses B's state machine. Use `reference_short` above for a native short test of the current ADC.

```powershell
.venv/Scripts/python.exe -m tools.saradc check
.venv/Scripts/python.exe -m tools.saradc prepare tt_short --view frozen-b --run-id sar8-frozen-short-v1
.venv/Scripts/python.exe -m tools.saradc sim tt_short --view frozen-b --run-id sar8-frozen-short-v1
.venv/Scripts/python.exe -m tools.saradc status sar8-frozen-short-v1
.venv/Scripts/python.exe -m tools.saradc analyze sar8-frozen-short-v1 --queue
.venv/Scripts/python.exe -m tools.saradc collect sar8-frozen-short-v1
```

The default `--view current` packages the actual `design/dut.scs` and its modules. Select `--view frozen-b` explicitly for frozen B. `check` verifies current ports and frozen provenance and reports separately whether the current design matches B. Daily design work can change declared module implementations.

The view registry selects the mixed hierarchy. Currently, `tt_short` supports `--view behavioral|comparator_xtor|cdac_xtor|sampler_xtor|control_xtor`. Other cases use the current transistor-level design or an explicit frozen regression. Mixed-hierarchy short tests use public-port observers. Use native transistor-level tests for Monte Carlo and terminal-voltage verification. [View registry](../specs/views.json)

Use per-module overrides and physical candidates when needed.

```powershell
python -m tools.saradc prepare tt_short --view current --view reference=va --view comparator=va --view timing=va --run-id NEW_ID
python -m tools.saradc prepare tt_short --view behavioral --view sar=xtor --view timing=xtor --candidate sar=b --run-id OTHER_ID
python -m tools.saradc block list
python -m tools.saradc block sim --module cdac --run-id NEW_BLOCK_ID
python -m tools.saradc block follow --run-id NEW_BLOCK_ID
python -m tools.saradc draw --check
```

The source netlists carry RNL drawing annotations. `draw` generates the schematic views, and `draw --serve` starts the official viewer locally. Simulation uses the separate managed entry point. [RNL schematic guide](schematics/README.md)

Select `xtor` or `va` for any of `sampler / cdac / comparator / sar / reference / timing`. The generated hierarchy preserves source netlist connections. RC and clear models use explicit, asymmetric rising and falling delays. Specify a physical candidate only for an `xtor` module. Use frozen regression with the frozen module selections. [Standalone block tests](../tb/blocks/README.md) · [Candidate conventions](../design/xtor/README.md)

Reuse the workspace's existing Virtuoso Bridge and ADE connection. The generated Spectre and Verilog-A netlists implement the same module selections. Record connectivity to the environment and OA synchronization with the text design as separate findings.

`sim` registers and submits a simulation once. Run analysis and collection explicitly. The executor rejects different inputs under the same ID. If the network response is uncertain, look up that ID before retrying. Run records and frozen packages are in `work/state/runs/` and `work/output/managed_execution/`.

```powershell
.venv/Scripts/python.exe -m tools.saradc observe modules
.venv/Scripts/python.exe -m tools.saradc observe cold
.venv/Scripts/python.exe -m tools.saradc observe refs
.venv/Scripts/python.exe -m tools.saradc checkpoint
.venv/Scripts/python.exe -m tools.saradc module-results
```

Use the existing launch receipt to connect to the read-only monitoring database. The cursors live in `work/state/timing_mc/`. The remote refs queue continues registered tasks. The old cold controller's held record identifies the historical run. Reuse the existing registrations when reorganizing local directories.

Local settings are in `site.local.yaml`. The remote T28 adapter uses the existing account, server workspace, and PDK restrictions. It allows seven heavy-task slots. An existing case uses four threads, 1 GiB for simulation, 256 MiB for analysis, and 32 MiB for collection. Admission also checks actual server resources. [Site configuration example](../site.example.yaml)

Analyzers accept `--run-dir DIR --output-dir DIR`. An analysis-only task also binds a real completed source. Raw waveforms stay on the server during normal collection, which retrieves compact results.

To collect all device terminals at the five corners for the minimal reference, use `python -m tools.saradc.soa prepare|submit --corner tt|ssc|ssh|ffc|ffh --revision NEW_ID`. It submits to `thu-song`, starts from the frozen minimal-design short test, and adds all MOS terminals while preserving the circuit and 18-frame stimulus. Use `--maxstep-ps` to tighten the time step. Treat the standard-cell library as read-only. Record terminal names and library digests. Keep the library parameters in their original files. The managed executor handles the run. When it finishes, use `analyze ID --queue` and `collect ID`.

The terminal-voltage analyzer finds piecewise-linear threshold crossings and cumulative duration in moving windows from native waveforms. It writes `derived/terminal_results.json` and `derived/result.json`. A missing required terminal or unclassified model fails analysis. Numerical passes carry a time-resolution review flag. Retain original CMI and LTE warnings. Report execution, correctness for the 18 frames, and terminal-voltage findings from their respective evidence. [Terminal-voltage engineering rule](../specs/soa_rule.yaml)

For a single-variable candidate on the same frozen stimulus, specify `--candidate reference=NAME` or another registered module. The flow resolves the actual archived replacement files by module interface, records before-and-after digests, and rebuilds the terminal list. Experiments use their declared implementations. The `reference_short.py` functional analyzer accepts managed `--source-run-dir` for independent timing analysis of a completed all-terminal run.

The same managed executor supports `thu-wei`, `thu-sui`, and `thu-song`. Use `engine().register(recipe, host='thu-song')` to choose the host for a new registration and `engine().storage(host='thu-song')` for storage initialization. Run records bind the host and route later queries, analysis, and collection automatically. Historical records without a host belong to `thu-wei`. Follow the transfer procedure below for an existing experiment.

The hosts share `/home` user directories and PDKs through NFS. Each host has its own `/server_local_ssd`. Queue locks and resource checks are per host. To transfer an unfinished experiment, keep the original record, register a new ID on the destination, and record the mapping. Stop the original task before starting the replacement. The stop interface acts on the matching worker and child processes after verifying start time, process group, account, and command. Keep raw logs and the cancellation reason.

For the current OR design's noisy dynamic test, use `python -m tools.saradc.noise_fft --run-id NEW_ID`. `--pilot` makes an eight-frame observer and protocol check with a 2 MHz low-frequency noise-shaping corner. The full package uses eight warm-up frames followed by 1024 consecutive frames with 10 kHz–2 GHz noise settings and noise seed 101. The observer uses the current interface after removal of the reference capture clock. Cross-check native waveform decoding against the Verilog-A output codes. `managed/noise_fft_follow.py` reads the frozen manifests of both registered IDs and submits the full run after the pilot passes. It then starts analysis. It uses the original continuous waveform and leaves retries and waveform retention to their respective procedures. [Noise FFT launch record](../results/noise/resetor_1024_launch_20261115.md)

Prepare full-circuit global-plus-local Monte Carlo with `python -m tools.saradc.mc_short --revision NEW_ID`. It uses three fixed voltage and temperature conditions, 12 seeds per condition, and ten points per seed. `managed/mc_short_follow.py` consumes exact registered IDs and expands each group once its first two samples pass. Check actual random coverage in the native parameter file. Report code offset and timing errors separately. Checkpoint queries resume work on existing batches. [MC launch and analysis-only reuse record](../results/mc/resetor_global_local_launch_20261115.md)
