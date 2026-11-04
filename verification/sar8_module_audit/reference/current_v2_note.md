# v2: keep current evidence, reduce unrelated voltage output

v1 failed due to output size, not a reported convergence failure: managed
`output_size_limit`,8,615,637,167 bytes,364.853s,peakRSS390,717,440 bytes.
Native SPECTRE-27 occurs at61.9763ns; SPECTRE-25 follows managed termination.
The64ns fault window was not reached, so v1 is not valid reproduction evidence.
Its raw history/logs are preserved. CAP_REQ and other SPECTRE-16780 LTE-relaxation
warnings, and CMI warnings from the physical load island, remain visible.

The separate v2 package changes **only voltage save selection and matching
measurement metadata**. DUT, PWL, analyzer, supply, sampling/closing timing,
solver settings and stop time are byte/hash unchanged. All non-save bytes of
test.scs match v1 exactly. Actual parent-frozen resources remain8GiB output,
1GiB simulation RSS and256MiB analysis RSS; no budget increase.

| Evidence | v1 | v2 |
| --- | ---: | ---: |
| Saved voltages |1100|138|
| Saved terminal currents |275|275|
| KCL nodes / complete incident terminals |5 /15|5 /15|
| Declared MOS terminal-pair screens |228|228|
| Fault diagnostic voltages / source-initial witnesses |43 /31|43 /31|
| Same-source voltage comparisons |21|21|
| Full-history KCL stream / native fault stream columns |27 /324|27 /324|

89 voltages meet analyzer/terminal-screen requirements.49 additional voltages
retain all previously saved selected-current port context, including driver0
Rgate junctions and all16 CDAC bottom plates. Two ideal source nodes VREFP_SRC/
VREFN_SRC were already unsaved in v1 and stay unsaved; their fixed levels remain
0.9/0V in the unchanged testbench. No missing current is filled with zero.

Removed962 unrelated voltage saves:305 load-controller internal,350 other-bit
driver internal,120 BBM internal,72 capture-DFF internal,59 other reference,
46 root/shadow boundary,10 unrelated bootstrap internal. Physical devices/loads
remain present. The remaining9078 source MOS pairs are not claimed to be fully
voltage-saved or screened in v2; this run targets driver0 branch attribution.
The full original log remains saved and is never replaced by a no-CMI verdict.

Total saved signals fall1375->413, a69.96% reduction. A PSF path-length/value-width
proxy gives71.23% reduction. Original **reference** native points through the v1
stop are111,083 versus129,379 to the target, a1.165 multiplier; these are not
measured v1 counts. Applying that proxy gives about2.69GiB complete v2 output,
with nearly3x growth margin to the unchanged8GiB cap. Actual v2 points/bytes are
unmeasured; no speed/accuracy or electrical pass follows from this estimate.

Use the full native history first. Output-window splitting is unnecessary for
this retry and would complicate startup/current coverage. No restart at64ns,
invented earlier currents or altered initial conditions is introduced.

Local ready files: `generated/current_v2/recipe_proposal.json`, measurement.json,
test.scs, save_audit.json and package_review.json. All six input hashes are
listed; complete input25,274,935 bytes. Frozen v1 inputs remain unchanged.
Parent owns managed registration/queue execution; no new remote action here.
