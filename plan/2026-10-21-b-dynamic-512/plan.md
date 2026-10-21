# B 1x coherent 512-point dynamic acceptance

## Authorization and ownership

User approved one native B/1x run: 4warmup+512observed frames,10MS/s,
near4.5MHz,-1dBFS. Keep all DUT topology/W/L/CDAC/reference network, ideal
clock/event models and solver precision unchanged. No PVT/mismatch/noise,
static sweep, width sweep, automatic retry, circuit repair, OA write or push.
Analyze the whole capture together; monitor actual progress and interrupt only
for clear failure/stress/invalid conversion, not expected fixed sampling lag.

Starting HEAD372f182, exp/cdac-flat8-device, index empty. Existing Obsidian
notes/moves/images and untracked cdac10_dualrail work are unrelated and must
remain untouched. Read-only dependencies: old B/short/W results and sources,
all PDK/shared libraries, bridge and ADCToolbox repositories. Remote OA owned:
none. Native scratch owned only unique exact run root/PID from this launch.

Owned local paths: this plan; config/b_dynamic_512.yaml;
scripts/integration/b_dynamic_512.py, b_dynamic_512_analyze.py and
b_dynamic_512_reduce.py; output/b_dynamic_512/ generated files;
verification/integration/b_dynamic_512_results.json; docs/b_dynamic_512.md;
docs/figures/b_dynamic_512/; narrow docs/project_status.md and plan/log.md.
One thread heartbeat may be created/updated for this exact approved run, with
quiet unchanged-state checks, meaningful-change/failure/completion notices.
No other automation or task is changed. Local focused commits only.

## Frozen bench

Use current native SAR_ADC_T28/sar_adc8_join_r3 B top and its existing TB.
T28TT,.9V,27C, main1um/L150nm, native StrongARM/SAR/CDAC/3x reference MOS,
50ohm input/reference resistances and4pF each reference rail. B restore100ps,
50ps reference edges/deadtime100ps, SAMPLE unchanged. APS4,+lqtimeout60,
conservative,maxstep10ps,gear2only, requestedreltol1e-5/effective1e-6,
vabstol10nV/iabstol100fA, gmin1pS unchanged. No strobeonly or model replacement.

N512, coherentbin231 (coprime), actualfin4511718.75Hz, Fs10MHz, differential
peak .9*10**(-1/20), CM.45V, original source phases -72/+108deg.516frames,
actual/declaredstop51600ns; retain original passive stop observer and all old
passive monitor/probe VA byte-identical. Only input frequency/amplitude and
stop observer parameter change. All native subckt blocks and clock/solver
statements must match immutable B; old artifacts never overwritten.

## Implementation and gates

1. Read skill/API instructions. Check healthy exact bridge/CIW/library/tech,
   windows, current top/TB/36dependencies/currentBVA hashes. Read native process
   list and existing flow before launch, no duplicate. Record disk/CPU/local
   memory/storage budgets first: prior136-signalPSF scales to~130GiB; localE
   currently~65GiB free. Use lossless compression/streamed per-frame reduction
   if remote scratch can support full-save raw, rather than whole-file RAM or
   local uncompressed storage. If resources cannot support safe full-save,
   freeze a smaller explicitly documented save-only surface before launch;
   never silently reduce DUT, solver precision, sample grid or claimed coverage.
2. Freeze config/deck/include hashes and analysis schema before native launch.
   One job only, timeout adequate for hour-scale native compute; hidden local
   coordinator, exclusive launch guard, exact native PID/log binding. No rerun.
3. Monitor real R3MEAS/BSINE516frames and bound PID/log. Stop exact owned
   Spectre only for fatal/convergence failure, CMI stress or confirmed invalid
   count/rail/timing/gross code event. Expected ~1.78ns fixed aperture delay and
   raw sine held-error are not stop criteria. Preserve failure/raw/log data.
   LTE precision notices require notification and validity review, no hidden
   parameter change. Check disk headroom; stop safely if data cannot be retained.
4. Preserve native result.ok classification. Parse full continuous data in
   bounded chunks, not one multi-GB list. Verify parser equivalence on existing
   native data and exact finite/monotonic/end/sample records. Retain original
   compressed PSF bytes and all native logs, with hashes and parser provenance.
5. After all516 frames: 8compare/write/update, MSB order, last update<60ns,
   stable90/98ns code/logic rails; report reference restore/event handling,
   selected analog terminal stress and native warnings, including initialDC
   Gmin/pivot notices. Keep core.99V vs IO1.98V engineering screens distinct.
6. Analyze exactly observed frames4..515 final codes, uniformly indexed by
   actual sample times (read latency separate). Coherent rectangular FFT with
   correct one-sided DC/Nyquist weights: SNDR/ENOB/SFDR and harmonic accounting;
   cross-check SNDR/ENOB with local ADCToolbox. Fit DC/gain/fixed delay separately;
   do not remove harmonics or re-time individual samples to improve SNDR.
   Report deterministic/no-transient-noise scope and any endpoint convention.
   SNDR>=43.9dB/ENOB>=7 per existing provisional project conventions, no claim
   of full-code DNL/INL/noise/PVT qualification.
7. Signed supply/reference/idealdriver/input source energy separated, include
   startup/warmup/observed and acquisition/conversion windows. Real drivers/
   reference-buffer overhead still missing, so do not claim physicaltotal<=1mW.
8. Whole-batch figures show ideal baselines, sample/read alignment, spectrum
   and selected frame details. Visually inspect; curate JSON/report/figures,
   update factual status/log, focused compile/math/parser/hash/diff checks,
   scoped local result commit only, no push. Mark flow complete then pause
   only this run's heartbeat; no archive and no further native experiments.

## Status

Prepared; no native job launched yet. Current B top/TB/36dependencies and
current VA byte hash match. Bridge0.8/t28_io/exactllm_IO CIW and Spectre21.1
healthy. No pre-existing native bridge jobs. Remote scratch has~409GiBfree,
localE~65GiBfree. Full136signal save is selected; old raw scales to~130GiB,
gzip1 sample ratio.2591 estimates~33.6GiB local archive. Remote raw+compressed
data remain until local gzip and complete decompressed SHA checks succeed.
After final curation, only this exact scratch root may be removed, keeping
verified full local gzip/log/receipts; no broad cleanup or other runs touched.

All native/clock/options/tran statements compare unchanged; sources fin and
amplitude plus passive stop parameter are the only bench electrical changes.
All5VA files copied byte-identical, no VA authoring or DUT behavioral rewrite.
Parser/currentPROP and arbitrary frame-boundary carryover tests pass, including
native frames0/4/8/15 power/held/CDAC cross-check against completed A16. Native
short-parser2048point equivalence passes. Actual gzip1.5/SCP/gzip/SHA fixture
roundtrip passes (small temporary data only, no extra simulation). FFT512
cross-check with local ADCToolbox, analytic DC/gain/delay/H2 alias and Nyquist
weight tests pass. Compile and frozen config/hash checks pass. One exclusive
native launch will follow a scoped preparation commit; no automatic rerun.
