# Idle-tail full characterization

Fixed candidate: `027b951`, DUT hash `ef0fc74a…76ea`. No OA change.
Original R4 fixtures/metrics remain read-only. New namespace is
`output/sar8_idle_performance/`, not `output/sar8_r4_performance/`.

Use workspace Python `E:/bridge-Agent-T28/.venv/Scripts/python.exe` for
`flow.py preflight`, `setup`, `smoke`, `status --batch smoke`, `collect --batch
smoke`, `smoke_gate`, and `full`, in that order. Setup/prepare/launch are
exclusive operations: never run them again after a manifest exists.

Full batch: one 1028-frame sine (4 warmup +1024 measured), eight static ranges
covering 255 transitions and 256 centers; total 3618 frames. Four detached
native lanes with four Spectre X CX threads per job. Lanes are balanced by
frame count, keeping the long sine separate. Each native job writes its own
exit code; batch completion alone is not success.

After dispatch:

```powershell
E:/bridge-Agent-T28/.venv/Scripts/python.exe scripts/sar8_idle_performance/flow.py status
E:/bridge-Agent-T28/.venv/Scripts/python.exe scripts/sar8_idle_performance/flow.py collect
.venv/Scripts/python.exe scripts/sar8_idle_performance/compare.py
```

`finish.py` is an optional one-shot local collector for this exact already
submitted batch. It polls, collects completed cases and invokes `compare.py`
with the project Python (ADCToolbox). It never starts/restarts Spectre. Launch
hidden, once; exclusive `collector_started.json` prevents concurrent readers
writing the same artifacts. If it stops or the PC sleeps, remote simulations
continue. Inspect `collector.log` and resume manual status/collection; do not
delete evidence or restart native cases. A partial download needs inspection,
not blind rerun of the original collector.

Final data: `verification/sar8_idle_performance/results.json`.
Final report: `docs/sar8_idle_performance.md`, three figures under its namesake
figure directory. Automatic completion is `complete_pending_visual_review`;
the agent still needs to inspect images, actual logs and scoped diffs, then
finish the plan/log/commit. No automatic Git push or R4/OA adoption.

The 98 ns digital output is valid after reference idle reset. The 98 ns analog
top-plate voltage is no longer a completed-conversion residue and is excluded
from performance comparisons. One-nanosecond strobes are not peak-stress
evidence; retain CMI diagnostics and prior separate high-resolution evidence.
