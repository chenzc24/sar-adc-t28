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

Complete: allthree nativecases parsed,metrics/4figures visuallyreviewed and
curated. Recommend2x asengineeringcandidate only, noOAadoption/specchange;
allthreefail theoriginaluncorrectedrawgate. See finalrecord below.

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

At13:50local W1/W2 native logs both zeroerrors/7warnings,24valid8compareframes,
solverparameterdifferences{},noCMI/LTE. Full~2GBraw andlogs downloaded; optional
missing.ic/.fc are skipped with bounded transport receipts, no manualkill/rerun.
W1serialparse began13:50:47 whileW3 nativeworker56028 started. W3 exactroot
b27ac040,Spectre226693,parent226636. W2waitingfor serialparse. Native log-probe
preliminary20point fit givesW1lag1.783593ns,gain-.153617%,remainingpeak158.561uV;
W2lag.882236ns,gain-.082646%,remainingpeak54.505uV. These stillawaitcontinuous
waveform cross-check; no widthdecision beforeW3. Analysisfigure labeling and
old500kHz-amplitude-condition metadata refined without changing immutableinputs.

By14:04local W1/W2bothparsed,result.ok true,parse325.57/328.06s. Independent
continuous-wave extraction cross-checks logprobes,actualSAMPLE/sourcehistory,
reportedsolverparams and24frameeventcounts. Held residualpeak158.560743/
54.504658uV,RMS110.740937/38.199917uV. Trackingresidualpeak156.309/42.335uV,
turnoffresidual17.095/18.399uV; highfrequencydiffers from500kHz attribution.
Nativecode error vsnominalsource max6/3codes,vsactualheld max1/1; inputpair
terminalpeaks.897741/.899580V. Do not interpret nominalsource codeerror asSAR
logicfailure. Preedgequadraticwindow sensitivity~90uV,cubic3/5/8ns~1.34uV;
primaryheld-fit metrics do not depend onthisextrapolation. W3now12/24normal,
noCMI/LTE; still no finalWrecommendation orOAchange.

Final at14:27local: allthree result.ok,24frames each/8compare-write-update,
stable90/98codes,zeroerrors/7existingwarningseach,noCMI-2754 orLTErelaxation,
reportedsolverparameterdiffs{}. Points1325663/1327374/1326635; sourceanalytic
samples andacrossW identicalhistory/times,hashes/probes andexactreconstruction
pass. Parse325.57/328.06/294.34s,oneparser only. Allrequiredraw/logs saved;
sixabsentoptional.ic/.fc skips,no timeouts/manualkills/native rerun;allthree
scopedremotecleanup returncodes0. Original500kHz inputs/results untouched.

Lag1.783592/.882235/.574250ns,gain-.153617/-.082646/-.085977%; nonfundpeak
158.561/54.505/40.619uV,RMS110.741/38.200/29.250uV. Phase-onlyerrorpeak
.195338/.100217/.102888LSB. Rawpeaks40.091849/19.834526/12.889723mV,
all20/20outside1.7578125mVgate. Do not declare originalacceptancepassed.
Trackingremaining156.309/42.335/20.205uV,turnoffremaining17.095/18.399/22.942uV;
quadraticpreedge sensitivity~90uV,cubicwindow<1.34uV,primaryheldfit independent.
Nativecode errorvsnominal6/3/2,vsheld1/1/1; inputpairterminalmax.897741/
.899580/.900352V <.99screen,not all-devicesignoff.

W2recommended engineeringknee: significantamplitude/residual improvementvsW1;
W3worsegain/phase-onlyamplitude andonly.001975LSBfurther nonfundpeak reduction.
W1nominalresidual also below8bitbudget;recommendation is not a uniquelyrequired
size orproof1xcan'tmeetENOB7. OAremains1x; noPVT/fullcode/FFT/noise/mismatch/
powerqualification. Report/metrics/4figs andnarrowstatus/log,focusedvalidation
andlocalresultcommit only. Non-overlapping usernotes/newplans preserved.
