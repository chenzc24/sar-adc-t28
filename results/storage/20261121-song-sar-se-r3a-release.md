# thu-song release of the typical-RC SS-cold SAR macro run, 2026-11-21

The raw waveform of `sar8-sepl-ssc-cw-verify-r3a`, the SS-cold post-layout run of `sar8_se_core/layout_r3` with the macro extracted at typical interconnect, was deleted under the [retention policy](../../docs/waveform-retention.md). `sar8-sepl-ssc-cw-verify-r3cw`, with the macro extracted at CWORST_T, replaces it. Its measurements and the frame-0 diagnosis stay in the [SAR macro record](../../Layout/results/sar_se_core.json). [Index and execution record](20261121-song-sar-se-r3a-release.json)

- Deleted and read back: `raw/tran_short.tran.tran`, 6,874,418,821 bytes, inode 4369643279; 6.40 GiB allocated.
- Free space on `/server_local_ssd`: 341.2 → 347.6 GiB.
- Before deletion the run had complete simulation and analysis, a local collection with its result and Spectre log, no analysis-only run built on it, no batch file naming it and no process holding its waveform.
- The server keeps a `raw_cleanup.json` marker; the managed runner refuses reanalysis of the run.
- Archive: `E:\bridge-Agent-T28\archives\sar8\20261121-song-sar-se-typical-ss\sar8-sepl-ssc-cw-verify-r3a.tar` (SHA256 `39f747ca7360f37271c6ba6d311912e127854d7373639146264490cd89beee2d`), with the local collection, registration and frozen deck.

The deleted waveform can no longer serve new signals or finer resolution; its results stand within the saved measurements.
