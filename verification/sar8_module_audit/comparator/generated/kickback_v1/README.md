# TT comparator with a held physical CDAC

Status: local executable package prepared; Spectre compilation and electrical
results are pending. Parent owns managed registration/submission.

The package contains two identical frozen D2 N4/rx2 blocks, including their real
receiver/register fanout. The evaluate arm receives the original clock; the
control arm stays in reset. Both have the original eighteen flat8 CDAC MOM
instances: binary weights plus dummy, 256 native unit instances per side.
Device geometry, multiplicity and comparator/receiver sizes are unchanged.

TT, 0.9 V, 27 C; input common mode0.45 V. Differential targets are
+1.7578125,+1.7578125,-1.7578125,+1.7578125,-1.7578125,-1.7578125 mV.
These are +/-0.25 LSB diagnostic inputs, not an allocated kickback budget.

## First cycle

| Time | Operation |
| --- | --- |
| 0--18 ns | Initialize both top plates through ideal controlled10-ohm conductances |
| 18--18.1 ns | Smoothly remove initialization conductance |
| 18.1--20 ns | Inputs hold charge on the actual MOM network |
| 20--20.1 ns | Original compare-clock rising edge on evaluate arm |
| 20.1--32 ns | Compare/write observation; initialization remains fully off |
| 32--32.1 ns | Original compare-clock falling edge |
| 44--44.1 ns | Start next acquisition, after the previous reset interval |

Clock starts remain20/60/100/140/180/220 ns, with0.1-ns edges and12-ns high
windows. Stop is260 ns. This is the existing block diagnostic schedule, not a
new ADC sample-rate or asynchronous timing specification.

Bit bottom plates are fixed at ideal0.45 V; the original dummy returns remain
VREFN=0 V and VREFP=0.9 V. The temporary initialization branches contribute zero
conductance during evaluation. Their series0-V sources measure branch current;
they do not connect the input to a fixed voltage. Bootstrap/sampler off-state
parasitics, reference switches/drivers and bottom-plate switching are outside
this isolated fixture.

## Inputs and measurements

- `recipe_proposal.json`: one managed TT run, six input polarities in one260-ns
  transient, one thread,1-GiB simulation RSS and256-MiB analysis RSS limits.
- `test.scs`, frozen `cells.scs`, `cdac_load.scs`, `initializer.va`: circuit and
  explicit testbench boundaries. Total registered inputs100,768 bytes before the
  runner adds its standard summary helper.
- `measurement.json`: exact input hashes, release/clock times, four complete
  top-node KCL equations,45 currents and228 N4/rx2 terminal-pair screens.
- `kickback_analyze.py`: Python2.7-compatible bounded native streaming analyzer.
  Dedicated output is capped at30 MiB; input raw data stays remote.

`result.json` reports initialized, just-released and pre-compare inputs; actual
pre-compare target error; differential/common-mode excursions relative to that
pre-compare point; and same-grid evaluate-minus-reset excursions. It also reports
raw output resolution, DATA at each estimated actual write crossing, late D0,
input-gate charge, top-node KCL, selected terminal peaks and original CMI warnings.
Reset levels of COMP_P/N and internal X/Y are recorded before comparison.

`wave.native.f64le.gz` retains every native timestamp. Column order and units are
in `wave.columns.json`; native extrema and KCL are never computed from decimated
plots. Crossing/at-edge DATA values are explicitly derived estimates, not a
storage setup/hold qualification. `spectre.original.log` preserves the native log.

The two-arm difference isolates the compare action under these fixed boundaries.
It does not establish ADC code error, stochastic noise, threshold offset/yield,
whole-circuit reliability, or response to a changing reference network.
`acceptance_pass` stays null. The initial local validation comprises nine targeted
structural/synthetic tests; no Spectre result is claimed.
