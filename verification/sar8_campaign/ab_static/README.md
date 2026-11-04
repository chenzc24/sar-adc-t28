# A/B TT full-code static scans in parallel with FFT — 2026-10-28

Finite server coordinator launched and identity verified, PID89555. Two low-end simulations are running: A sar8camp-a-tt-s001-003-v1 PID89559; B sar8camp-b-tt-s001-003-v1 PID89589. Existing A/B FFT PIDs65587/59993 remain running unchanged.

Each version first checks boundaries1..3. After its low segment passes, it advances at most2 independent static segments concurrently:4..35,36..67,68..99,100..131,132..163,164..195,196..227,228..255. Total18 existing immutable cases reused; no duplicates/new solver variants. Final aggregation verifies255boundary brackets,256center codes,monotonicity and reports DNL,endpoint INL,offset/gain and bracket resolution. Failed label stops expanding; in-flight data is preserved and other label can continue.

Static uses original strict Spectre X CX4threads, gear2only (conservative overrides retained and native actual settings recorded); FFT remains MX4threads. At full load4static+2FFT=6heavy simulations,24declared threads vs48account CPU quota. Shared managed gates check actual accountCPU,headroom,swapping,disk and other workloads. Existing B continuation later reuses same managed IDs, launch locks prevent duplicate processes. No modification of existing coordinators.

Resource preflight: user headroom17074728960bytes (~15.9GiB), host available104001363968bytes (~96.9GiB), swap rate0. Account memory.stat: cache32658153472bytes (~30.4GiB), anonymousRSS1802129408bytes (~1.7GiB). No cleanup/cacheflush/process kill needed or performed; filecache is not abandoned-process memory. CPU/memory/IO contention cannot be guaranteed zero, despite ample budget.

Server coordinator operates with laptop offline; heartbeat remains unchanged. No full-code results yet. No circuit/PDK/OA/baseline/automation change, commit/push or historical-data deletion. Artifacts: preflight.json,launch_status.json,coordinator_readback.json; manifest and launch receipt in parent directory. Source scripts: scripts/sar8_campaign/ab_static.py,deploy_ab_static.py.
