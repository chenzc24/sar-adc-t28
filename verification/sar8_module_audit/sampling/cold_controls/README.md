# SS cold controls

Local preparation only. Each new deck is an exact copy of its frozen hot source,
except simulatorOptions temp=125 becomes temp=-40. Source/diff/deck hashes are
recorded in manifest.json; no existing input was edited.

| New case | Frozen source | Initial history | Suggested run ID |
| --- | --- | --- | --- |
| low40cold | finite_history/low40/test.scs | High DC,40ns external low plateau | sar8audit-sample-v2-low40cold |
| longcold | stream_package/long/test.scs | Low-phase DC equilibrium | sar8audit-sample-v2-longcold |

SS MOS,0.81V supply,TT passives, input/reference sources/impedances, all devices,
loads, formal101/141ns source edges and measurement inputs are unchanged. The
fixture remains237MOS with comparator reset and fixedQ128 reference preset.
Recipe suggestions reuse the frozen stream package and loaded_remote.py.

Purpose: distinguish finite-precharge recovery from acquisition with a naturally
precharged low-DC state at the cold corner. Verify actual Cboot, BBOT, CTRL,
main G−VIN/current, actual SEQ low/high durations, preclose error and141.8ns
observation. Actual cold DC states and timing are unmeasured until the runs finish.
This pair does not establish full-ADC PVT or a minimum startup time.

Five local tests and byte-for-byte regeneration passed, including one-line
temperature delta, inverse recovery of each source, common-input reuse, exact
run suggestions and no invented qualification claim. No remote submission by
this session. New cold decks were not separately compiled by this task.
