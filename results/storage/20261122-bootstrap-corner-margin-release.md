# Bootstrap corner-margin waveform release, 2026-11-22

At the closeout of the [Bootstrap gate-margin record](../integration/bootstrap_corner_margin_20261122.md), the raw waveforms of its four SS-cold CWORST_T Bootstrap runs were deleted under the [retention policy](../../docs/waveform-retention.md). [Index, file identities and execution record](20261122-bootstrap-corner-margin-release.json)

- Deleted and read back: **4** `raw/tran_short.tran.tran` files, **20.15 GiB** allocated (thu-song 13.17 GiB, thu-wei 6.98 GiB).
- Free space on `/server_local_ssd`: thu-song 202.7 → 215.9 GiB, thu-wei 449.9 → 456.9 GiB.
- Before deletion, each run had complete simulation and analysis, a local collection with its result and Spectre log, no batch file naming it, and no process holding its waveform. The analysis-only gate jobs on `verify` and `extreme` had completed and were collected.
- Each run has a `raw_cleanup.json` marker on its server. `logFile`, `logStatus`, `spectre.out` and the derived results stay. The managed runner refuses reanalysis of a marked run. New signals, finer resolution or a new analysis need a new run.
- Archive: `E:/bridge-Agent-T28/archives/sar8/20261122-bootstrap-corner-margin/`. Each run has one tar with its local collection, registration, frozen deck and, where present, its gate job. Each of the four gate jobs on other experiments' runs is also archived (no raw data of its own). Every archive and member digest was read back before deletion; member digests are in the JSON.
- Not touched: the source waveforms of the other gate jobs (`sar8-allx-ssc-verify-a`, `sar8-sebit-ssc-cw-verify-b`, `sar8-sebit-ssc-cw-verify-bootx-a`, `sar8-sepl-ssc-cw-verify-r3cw`), which belong to other experiments, and the physical evidence `boot-core-20261121-cworst-t` / `-cbest-t` on thu-wei.

| Host | Run | Bytes | Inode | Archive SHA256 |
| --- | --- | ---: | ---: | --- |
| thu-song | `sar8-allxc-ssc-verify-a` | 7,071,036,415 | 2238007133 | `3610ceb68322fff9…` |
| thu-song | `sar8-allxc-ssc-extreme-a` | 7,072,878,463 | 6483791586 | `a606b37a2118a62e…` |
| thu-wei | `sar8-allxc-ssc-carry-a` | 7,067,111,636 | 440733201 | `ec70f4a6a552a808…` |
| thu-wei | `sar8-allxc-ssc-restart-a` | 426,565,073 | 6860848116 | `87b6c902bc2dad47…` |
