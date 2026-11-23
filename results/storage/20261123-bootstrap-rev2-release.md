# Bootstrap r2 waveform release, 2026-11-23

At the closeout of the [Bootstrap r2 record](../integration/bootstrap_rev2_20261122.md), on the user's request in the Bootstrap session, the raw waveforms of twelve requalification runs were deleted under the [retention policy](../../docs/waveform-retention.md). [Index, file identities and execution record](20261123-bootstrap-rev2-release.json)

- Deleted and read back: **12** `raw/tran_short.tran.tran` files, **60.40 GiB** allocated (thu-wei 19.74, thu-yuan 13.16, thu-tang 26.31, thu-shu 1.19 GiB).
- Free space on `/server_local_ssd`: thu-wei 332.6 → 352.3 GiB, thu-yuan 1444.2 → 1457.4 GiB, thu-tang 1375.6 → 1401.9 GiB, thu-shu 387.4 → 388.6 GiB. Other users were writing, so the changes are not exactly the deleted sizes.
- Before deletion, each run had a complete simulation and analysis and a local collection with its result and Spectre log. Its analysis-only consumers (`-gate`, `-split`) were complete, no batch file named it, and no process held its waveform.
- `sar8-bsr2-ssc-carry-f` is the exception: its simulation completed, but its queued analysis on thu-wei was cancelled at the user's request after the identical deck ran as `sar8-bsr2-ssc-carry-f2`. Its archive holds the collected Spectre log, states and deck, without a result.
- Each run has a `raw_cleanup.json` marker on its server. `logFile`, `logStatus`, `spectre.out` and the derived results stay. The managed runner refuses reanalysis of a marked run; new signals, finer resolution or a new analysis need a new run.
- Archive: `E:/bridge-Agent-T28/archives/sar8/20261123-bootstrap-rev2/`. Each run has one tar with its local collection, registration, frozen deck and, where present, its analysis-only consumers. Every archive digest and member digest was read back before deletion; the member digests are in the JSON.

| Host | Run | Bytes | Inode | Archive SHA256 |
| --- | --- | ---: | ---: | --- |
| thu-wei | `sar8-bsr2-ssc-carry-a` | 7,067,035,171 | 577057138 | `4e82080ad2b9ce42…` |
| thu-wei | `sar8-bsr2-tt-verify-a` | 7,062,979,221 | 577057127 | `74d266f5577d6e43…` |
| thu-wei | `sar8-bsr2-ssc-carry-f` | 7,067,124,319 | 577247939 | `d3ee2fd8d0b5aa09…` |
| thu-yuan | `sar8-bsr2-ssc-extreme-f2` | 7,072,426,939 | 7116488553 | `e76cac2f68ee8bb4…` |
| thu-yuan | `sar8-bsr2-tt-verify-f2` | 7,062,954,369 | 2573374429 | `0ebd3e3966469f03…` |
| thu-tang | `sar8-bsr2-ffh-verify-f2` | 7,060,175,940 | 2199918183 | `1f0636caf19d2ee1…` |
| thu-tang | `sar8-bsr2-ffh-extreme-f2` | 7,060,356,999 | 6457130378 | `52a3c60668ecd80a…` |
| thu-tang | `sar8-bsr2-ffh-carry-f2` | 7,059,660,349 | 2199918163 | `781ac3d7e59d5df7…` |
| thu-tang | `sar8-bsr2-ssc-carry-f2` | 7,067,124,320 | 4343471932 | `4e1a335e012829c9…` |
| thu-shu | `sar8-bsr2-ssc-restart-f2` | 426,572,073 | 5000709826 | `ca9619f0fac08a6d…` |
| thu-shu | `sar8-bsr2-ffh-restart-f2` | 426,296,914 | 2811087146 | `b48c64ed0db5b8ba…` |
| thu-shu | `sar8-bsr2-tt-restart-f2` | 426,335,994 | 5000709829 | `ec1e2d0441217d6d…` |

## Held

| Host | Run | Reason | Release when |
| --- | --- | --- | --- |
| thu-song | `sar8-bsr2-ssc-verify-a` | r2 without fill, SS-cold `verify` | the fill-residual cause is resolved or the user drops the item |
| thu-yuan | `sar8-bsr2-ssc-verify-f2` | r2 with fill, the same stimulus | same |

The pair is kept for an analysis-only look at the open cause of the fill's SS-cold residual increase (0.039 → 0.093 LSB).

## Not touched

- The Stage 2 session's runs (`sar8-s6e-*`), including the direct r2 runs `sar8-s6e-ssc-{extreme,verify}-r2`.
- The standalone sampler runs `boot-r2*-20261122`, about 9 MB each.
- Runs cancelled before they started, which have no waveform.
- The physical evidence on thu-wei (`boot-core-r2b-20261122*`, `boot-fill-r2-20261122*`, the chip probes).
