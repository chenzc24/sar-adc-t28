# TT native completion-feedback fixture

Local only; not Spectre compiled or submitted. Run proposal: recipe_proposal.json.
783 unchanged comparator/controller MOS +674 native receive/capture/BBM/front
MOS =1457. Three original comparator/clock MOMs,18 flat-CDAC MOMs and8x5fF
output loads. All8742 MOS terminal-pair screens are streamed at native points.

Physical cut: after complete first receiving inverters in each reference driver,
at GNPA/GPPA/GNNPRE/GPNPRE (32 nodes). Their two actual output drains remain;
two downstream gate terminals per node are removed. Drains solve natively under
zero external fanout: no ideal clamp, arbitrary capacitance or assumed slew.
manifest.json lists every retained/removed terminal and exact source identity.
This is a conditional load boundary, not complete reference-driver loading.

The reference request SR, delayed capture, ACK, all8 muxes/capture registers and
complete BBM cells remain to keep real PHI_U/D/CODE receiving dynamics. All8
capture reset ports are conditioned by declared SAMPLE_INT; preset sequencing
and external SAMPLE/RST_DONE handshake are excluded. First-arm input is held
+0.25LSB after18.1ns temporary initializer release; bottom rails remain ideal.
SAMPLE_INT falls20--20.1ns. Full native token/ACTIVE and RAW/DEC/PHI_W/PHI_U/
SR/QUIET/CMP_CLK feedback generates the eight decisions without fixed clocks.
100ns endpoint is an observation timeout, never a clock/reset control signal.

feedback_analyze.py streams native ASCII, deduplicates terminal-pair extrema,
records every timing/current row only for the selected timing columns, verifies
each token's write/update/reset and measured pre-next-clock recovery. Missing,
duplicate or wrong writes are reported as failures, never empty-list success.
Native logs/CMI/warnings retained. No noise/MC/PEX/PVT or final ADC accuracy claim.
Derived output hard cap29MiB leaves headroom under32MiB total collection target;
do not collect raw PSF. Simulation raw-output budget2048MiB is separate.
Parent alone registers/submits/analyzes/collects through managed serial execution.
