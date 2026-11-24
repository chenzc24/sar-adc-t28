# thu-song single-edge waveform release, 2026-11-21

On the user's request to release superseded simulations, the raw waveforms of five pre-adoption single-edge runs were deleted under the [retention policy](../../docs/waveform-retention.md). These runs used the single-edge netlist before the four terminal-voltage changes. The adoption record does not cite them, and the adopted netlist reran the same stimuli. [Index, file identities and execution record](20261121-song-single-edge-release.json)

- Deleted and read back: **5** `raw/tran_short.tran.tran` files, **23.40 GiB** allocated.
- Free space on `/server_local_ssd`: 399.6 → 423.0 GiB. Parallel simulations were writing, so the change is not exactly the deleted size.
- Before deletion, each run had complete simulation and analysis, a local collection with its result and Spectre log, no analysis-only run built on it, no batch file naming it, and no process holding its waveform.
- Each run has a `raw_cleanup.json` marker on the server. The managed runner refuses reanalysis of a marked run.
- Archive: `E:/bridge-Agent-T28/archives/sar8/20261121-song-single-edge-superseded/`, one tar per run with the local collection, registration and frozen deck. Member digests are in the JSON.

| Run | Superseded by | Bytes | Inode | Archive SHA256 |
| --- | --- | ---: | ---: | --- |
| `sar8-sebit-ffc-cw-scan-a` | `sar8-sebit-ffc-cw-scan-b` | 3,498,648,680 | 6467678822 | `15c5b2ab6ab94ef1…` |
| `sar8-sebit-ffc-cw-extreme-a` | `sar8-sebit-ffc-cw-extreme-b` | 6,547,905,053 | 91103439 | `89773878c6c402bd…` |
| `sar8-sebit-ssc-cw-verify-a` | `sar8-sebit-ssc-cw-verify-b` | 6,560,524,859 | 4359399023 | `9a18aebf295972a7…` |
| `sar8-sebit-tt-nom-verify-a` | `sar8-sebit-tt-nom-verify-b` | 6,548,865,103 | 6443172836 | `459c7ba542d341c2…` |
| `sar8-sebit-tt-nom-smoke-a` | `sar8-sebit-tt-nom-verify-b` | 1,974,531,757 | 4359198422 | `e5c2a71d37cd4502…` |

## Kept

- Runs cited by the adoption record: the SS hot and FF hot verifies, the 63/64 boundary, the SS-cold extreme history, the 24-stage settling reference, six mismatch seeds and two restarts on the predecessor netlist, and every "-b" run of the adopted netlist.
- `sar8-sepl-*-r3a`, the post-layout runs of `sar8_se_core/layout_r3`. The SS and FF waveforms can go once the worst-corner reruns replace them; the SS frame-0 warm-up analysis needs its waveform first.
- 23 tap-exploration runs (`sar8-setap-*`, `sar8-setref-*`, about 87 GiB) cited by the settling-reference and bit-6 reports. One of them has an unresolved recrossing anomaly; each needs an evidence check first.
- `sar8-setap-{ffc,ssc}-h8l5-verify-cold-v1` (7.8 GiB): not collected locally.
- Running and queued batch runs, which belong to another batch.

The deleted waveforms can no longer serve new signals or finer resolution; their results stand within the saved measurements.
