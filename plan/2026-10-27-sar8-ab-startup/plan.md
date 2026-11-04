# A/B low-first startup clock

User authorizes fixing startup by clock phase only. Keep frozen A/B DUTs,
PDK/library/OA/history read-only. No circuit changes, commit/push or adoption.
Owned: scripts/sar8_ab_startup/, verification/sar8_ab_startup/,
output/sar8_ab_startup/, management/recipes/sar8ab-startup-*.yaml,
management/runs/sar8ab-startup-*.yaml and corresponding managed outputs,
this plan and append-only plan/log.md. Other dirty module/manualADC/Obsidian/
10bit/shared management files are preserved. Existing A/B v1 flow continues.

Initial SAMPLE low; first rising edge starts101ns, first falling edge141ns.
Rise/fall100ps, high width39.9ns, period100ns: normal-cycle waveform is exactly
the original clock translated100ns. Valid frame origin100ns; source sequence
also translated100ns. First input held from t0. Initial interval is unscored,
but first valid frame MUST pass (not discarded). No forced internal controls.
Use identical ten low/mid/high frames on A/B. Existing VA observer unchanged;
discard only its pre-sampling record at98ns and rebase subsequent frame IDs.
Save bootstrap upper/lower plates to check precharge near100ns. DC initialization
at low clock is included; this is not a physical supply-ramp/POR qualification.

Copy analyzer into owned directory and generalize time origin; never modify
already registered inputs. Verify translated clock edge timings, both DUT hashes,
identical stimuli, analyzer timestamp/frame mapping and observer mapping.
Native managed run only, two heavy jobs total,4threads,1GiB sim,256MiB analysis,
32MiB collect,2GiB output. Serial finite runner waits existing A/B collection
before new pair, preserving original comparison and avoiding duplicate submission.
Acceptance: native completion, observer agreement, first and subsequent code
correctness, eight ordered conversions, stable output, measured sample close
and acquisition/tail settling compared with originals. Stress retained/deferred.
Artifacts: per-run JSON/CSV, startup summary and A/B plots after completion.
