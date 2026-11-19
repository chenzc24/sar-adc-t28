# Waveform Retention and Cleanup

On 2026-11-15, the user authorized deletion of large raw waveforms after archiving the evidence required for the conclusions and figures. This policy applies to this project's runs in the authorized account.

## Cleanup Eligibility

At experiment closeout, clean up a run when all of the following hold. Eligibility depends on evidence and consumers, independent of file age.

1. **Measurements are complete.** Simulation and required analysis have finished. Results, pass or fail verdicts, and coverage gaps are recorded. Diagnosed and closed failures are eligible on the same basis.
2. **Evidence is archived.** Collect the compact data, figures, original warnings, and input identities listed below to a durable location and verify file existence and digests. A sole copy on server scratch is insufficient. For cases where figures do not apply, record the reason.
3. **Consumers are finished.** Check the source run, its dependent tasks, and pending batches. Confirm that no running, queued, or planned analysis-only task, control, time-step review, or debug session needs the waveform and that no hold is active.

The current baseline is eligible once it meets the archive requirements. Retain waveforms for active runs, unfinished analysis, unresolved anomalies, disputed findings, and required reanalysis. Record the hold reason and release condition. If network, status, or dependencies are uncertain, hold that run and continue processing other eligible runs.

The user has authorized routine cleanup under this policy. Obtain separate authorization for exceptions outside the project or account or when raw evidence is still needed.

## Evidence to Retain

| Category | Required evidence |
| --- | --- |
| Run and reproduction conditions | Host, run ID, recipe hash, design commit and input digests, frozen netlist, stimulus and analyzer, model and library paths and identities, engine version and options, PVT, seed, and statistical mode |
| Conclusions | Values, thresholds, pass or fail status, unknown items, scope, and report links |
| Warnings and execution | Original Spectre logs, simulation and analysis status, exit codes, analysis-only source binding, and collection receipts |
| Compact data for reproducing figures | Values, units, sample times, plotting scripts or settings, and the relevant figures |
| Cleanup receipt | Exact paths, file identities, archive digests, verification of deleted and retained files, and space change |

Save the compact data needed by the experiment.

- **FFT.** Keep the actual output codes and sample times used in the FFT, input frequency, sample rate, selected range, window and bin groupings, metrics JSON, and spectrum.
- **Static tests and MC.** Keep conversion boundaries, codes or bit weights, per-seed measurements, and failed sample identities along with any summary statistics.
- **PVT and timing.** Keep per-frame codes, sampling close edges, per-bit handshake, decision, and settling measurements, minimum margin, and waveform excerpts for anomalous frames and bits.
- **Terminal voltages.** Keep peaks by device and terminal pair, over-limit intervals, window statistics, rule version, time-step review, and native-time excerpts of worst and anomalous events. Retain enough context before and after each event for the full evaluation window. Preserve narrow peaks at their native resolution.

Put reports and compact data in `results/` or a registered durable location. Keep large waveforms outside Git. Reference foundry models and library content read-only and store licenses and credentials outside the repository.

An archive supports its saved signals and measurement scope. If new signals or higher resolution are needed, start a new run with frozen inputs. Keep original conclusions bound to the original run and label the new data with its own identity.

## Checklist

Use `work/storage/` for drafts and `results/storage/` for completed receipts and archive indexes. Record at least these fields per batch. Substitute verified values before execution.

```json
{
  "schema_version": 1,
  "host": "thu-song",
  "run_id": "EXACT_RUN_ID",
  "recipe_hash": "SHA256",
  "conclusion": "REPORT_PATH",
  "archive": [{"path": "PERSISTENT_PATH", "sha256": "SHA256", "bytes": 123}],
  "consumers": [{"run_id": "ANALYSIS_ID", "status": "complete"}],
  "planned_consumers": [],
  "hold_reason": null,
  "targets": [{"path": "ABSOLUTE_WAVEFORM_FILE", "bytes": 123, "device": 1, "inode": 2, "mtime_ns": 3}],
  "status": "reviewed_not_deleted"
}
```

1. List reclaimable space. Start with superseded large waveforms and redundant debug runs. Check eligibility one run at a time. Keep logs in `runs/`, `raw/`, and `test.raw/` by targeting individual manifest entries.
2. On the actual host, verify account, canonical absolute path, run identity, byte size, device, inode, and mtime. Reject symbolic links and paths outside the run. Exclude active readers and writers. Prevent new consumers during cleanup and require exclusive access before deletion. Register older directories by exact path.
3. Delete waveform files listed in the manifest. Protect netlists, PDK and standard-cell files, OA, logs, compact results, figures, run records, and user notes. Use bounded streaming for excerpts and large digests. Keep reanalysis in the managed flow.
4. Record success, failure, or skip per file. Read back deletion and retention state. Measure logical bytes, allocated bytes, and actual free-space change separately. Concurrent writes or open files may delay free-space recovery.
5. Keep original simulation and analysis status. Record `raw_deleted` in the cleanup receipt with the date, archive path, and reanalysis scope lost. Assign new IDs to new runs. Use an applicable archive or run new data when the raw source has been deleted.

The managed run directory's `raw_cleanup.json` protects execution. If present, including while cleanup is in progress or partially failed, it blocks resubmission and registration as a fresh raw analysis source. Status queries retain the original completion or failure verdict and show the cleanup record. Keep this marker with the run.

## Capacity and Frequency

Review capacity at batch closeout and before submitting the next large batch. Use the expected growth of running tasks, the next batch's output budget, and managed disk headroom rules along with current `df`.

When space is short, start with eligible archived runs. Then reduce concurrency, adjust saved signals, or leave tasks queued as needed. Retain pending evidence and record failures. Apply the current resource limits.

The managed executor enforces disk admission and limits during runs. Use the manual or agent checklist to delete eligible waveforms. Maintain a durable archive under this policy while server scratch retention and backup guarantees are unconfirmed.
