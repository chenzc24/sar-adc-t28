# B high frequency main sampling width comparison

## Goal and boundaries

Compare main sampling W=1/2/3um at exactly4.5MHz,-1dBFS differential sine,
10MS/s. User requires topology,L,CDAC,external timing and simulator precision
unchanged. Separate single-frequency equivalent lag,gain,DC and nonfundamental
residual before recommending W. No full-code,FFT qualification,PVT,mismatch,
noise,automatic rerun,OA adoption,push or new automation.

Starting branch exp/cdac-flat8-device,HEAD recorded in generated context.
Dirty Obsidian_docs moves/deletions/notes/images and cdac10_dualrail files are
unrelated user work; preserve all. No overlap with this target's new sources.
Own this plan;config/b_hf_main_w.yaml;scripts/integration/b_hf_main_w.py;
scripts/integration/b_hf_main_w_analyze.py;docs/b_hf_main_w.md;
docs/figures/b_hf_main_w/;verification/integration/b_hf_main_w_results.json;
narrow docs/project_status.md and plan/log.md entries. Generated
output/b_hf_main_w/ only. Remote OA owned:none. Remote writes only bridge-owned
unique native Spectre scratch. PDK,other libraries,all previous sources/runs and
automations read-only. Do not modify the design_spec or original raw-error gate.

## Conditions and implementation

1. Read applicable AGENTS,README,specifications and prior500kHzwidth workflow.
   Spectre skill uses native PDK solver,not unsupported EVAS transistor emulation.
   Document skill honors repository-local plan/report format,not a cloud Page.
2. Initial tunnel down;one scoped bridge start restored0.8.0/t28_io,daemon,
   CIWthu-wei/userchenzc_intern25/TSMC28/llm_IO andSpectre21.1 healthy.
   Only CIW window present. Read-only verify B top/TB and36dependencies against
   immutable baseline before launching; no OA edits.
3. Reuse validated B24frame deck/includes as immutable template,not simulation
   results. All three widths require new4.5MHzruns. Only testbench source freq
   and amplitude change from500kHz: differentialpeak .9*10**(-1/20), perleg half,
   CM.45V,source phases-72/108 unchanged. Keep declaredVDIFF=.8 since it is unused
   by continuous sources; document actual source amplitude independently.
4. W1/2/3um,nch_18_mac,L150nm,nf1,multi1; resize only sharedMmain W and
   AD/AS=W*155nm,PD/PS=2*(W+155nm),previous PDK geometry validation retained.
   BothP/N maininstances change together; otherMOS,CDAC18multi groups,equivalent
   512MOMunits,1pFbootstrap,StrongARM/nativeSAR/ideal referencegateB unchanged.
   Input50ohm each;reference50ohm+4pF each unchanged.
5. Keep4warmup+20observedframes,24total/2.4us.20observations cover9inputcycles,
   exact bin9/20 coherence; not one4.5MHzcycle. Keep sourcecontinuous fromt0.
   Declaredstop51.6us/passivefinish2.4us,44continuous saves,APS4,conservative,
   maxstep10ps,gear2only,requestedreltol1e-5,effectivebaseline1e-6,
   vabstol10nV/iabstol100fA,TT/.9V/27C unchanged.
6. At most2native compute/download workers and1local parser. Nativepipeline
   overlaps thirdcompute with serial localparse when possible. Use inspected
   bridge0.8.0 remote-run/result helpers,same nativeCLI andresult.ok semantics.
   Scope a transfer wrapper only: bound optional.ic/.fc downloads to45s,
   requiredlog60s/raw900s,and own-scratchcleanup30s; retain skip/failure receipts.
   Never change simulator timeout,solver,saves or raw data to accelerate parsing.
   No generic process kills or repeated simulation launches.
7. Fresh progress uses exactcase remote log/deck/PID,24R3MEAS/BSINErecords,
   native footer,CMI/LTE/convergence andreportedsolverparams. Localstage timestamp
   is not a nativeheartbeat. Failed query is unknown,not zero-progress/success.
8. Frequency-awareDC+sin/cos fit at4.5MHz,phase-only diagnostic retaining gain,
   residualpeak/RMS/LSB,rawuncorrectedgate andnativeoutputcode/timing screens.
   Same+.6ns heldread. Sourceanalytic samples andsamehistory acrossW verified.
   Preedge5ns..-.15ns cubic tracking prediction is diagnostic only; check
   3/5/8ns windows and2/3/4/5degrees because highfrequency curvature can bias it.
   Do not label turnoffincrement pureinjection or nonfundremainder purestaticINL.
9. Compare500kHz and4.5MHz transfers without claiming broadband pureconstant
   delay. No ENOB/SNDR from20analog samples. Both originaluncorrectedcriterion
   andphase/gain-separated interpretation retained when recommending width.

## Validation and artifacts

Validate exact3decks differ only sourcefreq/ampl plusmainW-derived geometry,
hashes/includes/nativeblocks/save/clock/precision unchanged. Focused compile,
frequency-aware synthetic lag/gain/DC/H2/H3 recovery and500kHzmath equivalence,
9/20coherence and -1dBFS arithmetic checks before launch.
After run require result.ok,24frames,8compare/write/update andstablecodes or
report explicit failures; retain allnumericalwarnings. Validate sourcehistory,
actualSAMPLE50%times,rawprobe/waveform agreement,fitreconstruction/orthogonality,
width/inputs/source receipts andvisually inspect figures with realbaselines.
Candidate choice is not fullADCqualification or permission to adopt OA.
Save smallmetrics/report/figures,updateplan/log/status,focusedgitdiffcheck and
localbounded commits only. No PDKmodel contents,license data,rawOA orPSF inGit.

## Status

Launched2026-10-21 13:20:04Asia/Shanghai,local launcher31348/coordinator13112.
W1nativeworker42016,remote b4ed7f44/Spectre322222(parent322164).
W2nativeworker57580,remote7ca28707/Spectre322218(parent322160).
W3queued; no duplicate500kHz reuse. At13:20:34 firsttwo native processes active,
0/24completedframes, no observed warning yet; not a completed performance claim.
CurrentB top/TB/36dependencies match,libtsmcN28/CIWllm_IO confirmed read-only.
Exact native logs/process bindings stored percase inoutput/b_hf_main_w/remote.json.

Input identity/geometry/unchanged precision checks pass;frequency-aware synthetic
DC/gain/lag/H2/H3 recovery and500kHz prior-threecase mathematicalequivalence pass.
Transport-only fake-runner test verifies optional timeout isolation, requiredraw/
log retention andunchanged14400snative timeout. Localfree~13GB/32GBRAM,Efree92GB;
parsing serialized. Scoped diffcheck clean; unrelated Obsidian trailingwhitespace
was observed by globaldiffcheck andleft untouched. Complete results pending.
