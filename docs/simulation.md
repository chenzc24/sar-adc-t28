# Simulation and Monitoring

At experiment closeout, before submitting a large batch, or when reclaiming disk space, archive the evidence needed for measurements and figures. Use the retention checklist to release eligible raw waveforms. The current managed executor leaves deletion to the checklist. [Waveform Retention and Cleanup](waveform-retention.md)

`specs/pvt_short.json` is the 45-point matrix that the reset-OR design ran: the original five corners plus 40 more, each with ten code centers, a 1.059 µs duration, a 10 ps maximum step, four threads, and a 4 GiB output budget. Its preparation entry was removed with that design, so a sweep of the current design needs a new entry built on `single_edge_lpe`. Use the all-terminal flow for a device-by-device terminal-voltage verdict. The references are fixed at 0 V and 0.9 V, passive models use TT, and the setup has a single supply domain with no separate 1.8 V rail.

`tools/saradc/managed/batch_follow.py` schedules a finite batch on the server. It reads registered run IDs and recipe hashes, uses managed admission, simulation, and analysis, and starts analysis automatically. Each batch has one controller lock. It retains failures and uncertain results for review and continues other corners. Use the retention policy after collecting and archiving the complete results.

Use `python -m tools.saradc behav generate` to synchronize Verilog-A and Python behavioral views with the specification. Use `behav check` for numerical cross-checks, `behav sim --run-id sar8-modules-v3` for native module and mixed-hierarchy verification, and `behav follow --run-id ID` to wait once, analyze, and collect. Review failures before rerunning. Registered IDs bind frozen inputs. Assign a new ID after changing the source. [Behavioral models](../design/behav/README.md)

Run `.venv/Scripts/python.exe -m tools.saradc` from the project root. The managed executor uses unique run identities, frozen inputs, resource queues, independent analysis, and digest-verified collection.

For the current design, use the single-edge entries. `single_edge_lpe` runs foundry cell LPE with the extracted CDAC; `reference_short` is the schematic-CDAC short test with its own event counts. Both use the 45 ns sampling phase from `specs/arch.json`. [Simulation entries](../design/xtor/README.md#simulation-entries)

```powershell
.venv/Scripts/python.exe -m tools.saradc.single_edge_lpe tt verify --cdac nominal --revision NEW_ID
.venv/Scripts/python.exe -m tools.saradc.reference_short prepare --version current --corner tt --revision OTHER_ID
```

`Layout.tools.simulation.prepare_all_extracted` builds the same deck with every frozen block extraction at the paired interconnect corner (`tt`, `ssc`, `ffh`): the coupled XREF/CDAC, the comparator with VDD/VSS RC and the SAR macro. The Bootstrap on both channels is its typical extraction `boot-core-20261121` by default; `--corner-bootstrap` uses its CWORST_T or CBEST_T re-extraction instead (run family `allxc`). `--bootstrap ID` requalifies a revised core: its typical extraction at TT and its re-extractions `ID-cworst-t` and `ID-cbest-t` at SS cold and FF hot (run family `bs<revision>`, for example `bsr2`). `gain` prepares the standalone XREF/CDAC weights that set k for each corner. `--route-scale` adds RC wiring at a multiple of the planned floorplan lengths. `split`, `routes` and `gate` are analysis-only jobs on a completed run. `split` separates the static reference-pin offset from plate settling. `routes` measures the top-level route delays. `gate` measures the main-switch gate discharge of both Bootstrap channels after each sample close. `--submit HOST` registers and queues the result. `Layout.tools.analysis.stage2_summary` writes the record from the collected runs. [Stage 2 results](../results/integration/stage2_all_extracted_20261122.md) · [Bootstrap corner extractions and gate margin](../results/integration/bootstrap_corner_margin_20261122.md)

```powershell
.venv/Scripts/python.exe -m Layout.tools.simulation.prepare_all_extracted adc ssc verify --revision NEW_ID --submit thu-song
.venv/Scripts/python.exe -m Layout.tools.simulation.prepare_all_extracted adc ssc verify --revision NEW_ID --route-scale 1 --submit thu-wei
.venv/Scripts/python.exe -m Layout.tools.simulation.prepare_all_extracted split RUN_ID --submit SAME_HOST
.venv/Scripts/python.exe -m Layout.tools.simulation.prepare_all_extracted adc ssc verify --corner-bootstrap --submit thu-song
.venv/Scripts/python.exe -m Layout.tools.simulation.prepare_all_extracted adc ssc verify --bootstrap boot-fill-r2-20261122 --revision f --submit thu-song
.venv/Scripts/python.exe -m Layout.tools.simulation.prepare_all_extracted gate RUN_ID --submit SAME_HOST
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
python -m tools.saradc prepare tt_short --view current --view reference=va --view comparator=va --run-id NEW_ID
python -m tools.saradc prepare tt_short --view behavioral --view sar=xtor --candidate sar=single_edge --run-id OTHER_ID
python -m tools.saradc block list
python -m tools.saradc block sim --module cdac --run-id NEW_BLOCK_ID
python -m tools.saradc block follow --run-id NEW_BLOCK_ID
python -m tools.saradc draw --check
```

The source netlists carry RNL drawing annotations. `draw` generates the schematic views, and `draw --serve` starts the official viewer locally. Simulation uses the separate managed entry point. [RNL schematic guide](schematics/README.md)

Select `xtor` or `va` for any of `sampler / cdac / comparator / sar / reference`. The generated hierarchy preserves source netlist connections. Specify a physical candidate only for an `xtor` module. Use frozen regression with the frozen module selections. [Standalone block tests](../tb/blocks/README.md) · [Candidate conventions](../design/xtor/README.md)

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

To collect all device terminals, use `python -m tools.saradc.soa prepare|submit --corner tt|ssc|ssh|ffc|ffh --revision NEW_ID --source-run-id SHORT_RUN`. It submits to `thu-song`, starts from the named prepared short test (without `--source-run-id`, the reset-OR minimal-reference run of that corner), and adds all MOS terminals while preserving the circuit and 18-frame stimulus. Use `--maxstep-ps` to tighten the time step. Treat the standard-cell library as read-only. Record terminal names and library digests. Keep the library parameters in their original files. The managed executor handles the run. When it finishes, use `analyze ID --queue` and `collect ID`.

The terminal-voltage analyzer finds piecewise-linear threshold crossings and cumulative duration in moving windows from native waveforms. It writes `derived/terminal_results.json` and `derived/result.json`. A missing required terminal or unclassified model fails analysis. Numerical passes carry a time-resolution review flag. Retain original CMI and LTE warnings. Report execution, correctness for the 18 frames, and terminal-voltage findings from their respective evidence. [Terminal-voltage engineering rule](../specs/soa_rule.yaml)

For a single-variable candidate on the same frozen stimulus, specify `--candidate reference=NAME` or another registered module. The flow resolves the actual archived replacement files by module interface, records before-and-after digests, and rebuilds the terminal list. Experiments use their declared implementations. The `reference_short.py` functional analyzer accepts managed `--source-run-dir` for independent timing analysis of a completed all-terminal run.

The same managed executor supports `thu-wei`, `thu-sui`, `thu-song`, `thu-yuan`, `thu-tang`, `thu-shu`, `thu-xia` and `thu-ming`. The five added on 2026-11-22 are reached through `thu-han` (SSH `ProxyJump`), share `/home`, the Cadence installation and the PDK, and passed a Spectre license checkout; `thu-qi` and `thu-liang` hang at license checkout and are not used. Before the first registration on a host, create `/server_local_ssd/chenzc_intern25` (mode 700) and run the storage initialization. Use `engine().register(recipe, host='thu-song')` to choose the host for a new registration and `engine().storage(host='thu-song')` for storage initialization. Run records bind the host and route later queries, analysis, and collection automatically. Historical records without a host belong to `thu-wei`. Follow the transfer procedure below for an existing experiment.

The hosts share `/home` user directories and PDKs through NFS. Each host has its own `/server_local_ssd`. Queue locks and resource checks are per host. To transfer an unfinished experiment, keep the original record, register a new ID on the destination, and record the mapping. Stop the original task before starting the replacement. The stop interface acts on the matching worker and child processes after verifying start time, process group, account, and command. Keep raw logs and the cancellation reason.

The reset-OR design's noisy dynamic test used `python -m tools.saradc.noise_fft --run-id NEW_ID`. The entry still expects that design's 40 ns sampling phase, internal probe nets and adoption-record format, so adapt it before running the current design. `--pilot` makes an eight-frame observer and protocol check with a 2 MHz low-frequency noise-shaping corner. The full package uses eight warm-up frames followed by 1024 consecutive frames with 10 kHz–2 GHz noise settings and noise seed 101. The observer uses the current interface after removal of the reference capture clock. Cross-check native waveform decoding against the Verilog-A output codes. `managed/noise_fft_follow.py` reads the frozen manifests of both registered IDs and submits the full run after the pilot passes. It then starts analysis. It uses the original continuous waveform and leaves retries and waveform retention to their respective procedures. [Noise FFT launch record](../results/noise/resetor_1024_launch_20261115.md)

The reset-OR design's full-circuit global-plus-local Monte Carlo used three fixed voltage and temperature conditions, 12 seeds per condition, and ten points per seed. Its preparation entry was removed with that design; for the current design, use `single_edge_lpe --seed` at the cold corners. `managed/mc_short_follow.py` consumes exact registered IDs and expands each group once its first two samples pass. Check actual random coverage in the native parameter file. Report code offset and timing errors separately. Checkpoint queries resume work on existing batches. [MC launch and analysis-only reuse record](../results/mc/resetor_global_local_launch_20261115.md)
