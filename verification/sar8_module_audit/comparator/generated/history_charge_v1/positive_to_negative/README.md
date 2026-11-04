# Opposite history: controlled charge, native feedback

Local only, not Spectre compiled/submitted. Parent dispatches after standard-cell
FF priority work. Same1457MOS/cells/RCs/receive chain,18 native MOM parameters,
100ns/settings/1GiB/one-thread/2048MiB raw budget and original SAMPLE_INT closing
20--20.1ns and initializer release18--18.1ns. No new baseline/noise/MC/PVT claim.

history_interface.scs copies the native root body and only exports CMP_CLK and
PHI_U as passive TB observation ports. Original cells.scs stays byte-identical;
flattened native devices/loads are identical under this two-node alias map.
XHISTORY connects ordinary top-level ports, not ambiguous hierarchical stubs.

Only input history differs between the two cases: HSIGN=-1 gives -8LSB then
nominal+0.25LSB; HSIGN=+1 is symmetric. 8LSB=56.25mV,32x small residual, initially
TOP421.875/478.125mV around450mV. Bit bottoms255Cu and dummy1Cu are unchanged.
alpha=255/256; equal/opposite29.1176470588mV bottom shifts give ideal target
+/-1.7578125mV and zero common-mode shift. Actual gate charge/parasitics are not
corrected: report absolute second TOPP/TOPN/DM/CM and target deviation as measured.

history_charge.va observes the first PHI_U rise then the following CLK fall at
0.1VDD, waits900ps, slews200ps once, then holds bottom voltages constant. Drives
only BOT_P/BOT_N and an isolated marker; no TOP/clock/token force. No sampler
window change. TOP initialization is never reattached; zero-conductance init
branch/current and real phase order are checked in analysis. This is a TB charge
history experiment, not actual transistor reference switching or ADC bit weights.

127V/23I native saves;990 selected direct-chain stress screens, remaining7752
unmeasured. Original full-circuit CMI logs retained. All-native metrics; two-pass
bounded60-column export <=30000 rows/14MiB, derived29MiB, collection32MiB. Native
protocol reducer is unchanged; runtime adapter changes only expected history/D
polarity and adds stimulus phase/actual-residual diagnostics. Success cannot be
claimed if the step overlaps comparison/write or is incomplete at second input.
