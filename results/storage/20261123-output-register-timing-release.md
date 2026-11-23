# Output-register timing waveform release, 2026-11-23

At the closeout of the [output-register timing record](../../Layout/results/output_register_timing.md), the raw waveforms of its two runs were deleted under the [retention policy](../../docs/waveform-retention.md), with the user's go-ahead in the chip-objects session. [Index, file identities and execution record](20261123-output-register-timing-release.json)

- **Deleted and read back:** 2 `raw/tran_short.tran.tran` files on thu-wei, 13.58 GiB allocated. Free space on `/server_local_ssd` went from 351.7 to 365.3 GiB.
- **Checks before deletion:** simulation and analysis complete; recipe hash matching the registration; the analysis-only `-timing` consumer complete and collected; no batch file naming the run; no process holding the waveform.
- **Markers:** each run has a `raw_cleanup.json` marker. `logFile`, `logStatus`, `spectre.out` and the derived results stay. The managed runner refuses reanalysis of a marked run.
- **Archive:** `E:/bridge-Agent-T28/archives/sar8/20261123-output-register-timing/`. Each run has one tar with its local collection (result and Spectre log), registration, frozen deck and its `-timing` job. Archive and member digests were read back before deletion.
- **Not touched:** the failed and cancelled FF-hot attempts `sar8-oreg-ffh-a` (thu-wei), `-ffh-b` and `-ffh-c` (thu-song). They hold no complete waveform, are about 33 MB each, and stay as failure evidence.

| Host | Run | Bytes | Inode | Archive SHA256 |
| --- | --- | ---: | ---: | --- |
| thu-wei | `sar8-oreg-ssc-a` | 7,298,751,565 | 2701964316 | `e3aac067fedca1a3…` |
| thu-wei | `sar8-oreg-ffh-d` | 7,287,884,085 | 4848806167 | `965589d24d610c31…` |
