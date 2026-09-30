# Active sampling architecture: top-plate

Decision date: 2026-09-30. The active SAR-ADC sampling design line is
**conventional top-plate sampling**. VINP/VINN connect through one input
bootstrap switch per side to the comparator-side top nodes of the 5+5
split CDAC during acquisition. The CDAC bottom plates start at VCM;
after input isolation, SAR reference switching at the bottoms moves the
held top-node differential for successive decisions. The sampled
top-plate polarity is `TOPP−TOPN ≈ VINP−VINN`.

`sar_cdac_bottom_plate_eval_10b`, its clamp variants, and their mixed
testbenches are retained as **historical experiments**, not concurrent
production ADC architectures. Their output and report provenance remain
unchanged. The old `XTOP` name meant “top-plate control” inside that A/B
fixture; it is the circuit path now being advanced. The active work uses
top-plate-only copied netlists so `XBP` and its unrelated warnings do not
obscure this path. No OA cellview has yet been promoted as the final
sampling switch or CDAC.

## Current gate-control boundary

The protected Bootstrap pump and main `MN11` are T28 model devices.
`GMAIN` is separate from pump `G`, and `OFF_MAIN` turns the main path off
before PHIB resets BOOT. In the prior full-CDAC five-point top-plate
fixture, ideal `STRACK` (`G→GMAIN`) and ideal `SHOLD` (`GMAIN→VIN`)
gave at most **0.174132 mV** uncorrected hold error, below the
0.439-mV deterministic allocation. The top-only +0.8-V reproduction
is **0.174102 mV**. Those are mixed T28-core/ideal-control Spectre
bounds, not full transistor-level verification.

The first actual T28 pass-device screen is in
`docs/top_plate_gmain_device_screen.md`. A single 0.9-V-gated NMOS cannot
pull boosted GMAIN down to high VIN; a single PMOS with ideal gate
steering cannot reach low VIN. A complementary NMOS+PMOS path can bring
GMAIN close to VIN, but the five-point `multi=4` raw hold error still
reaches **0.842425 mV** at ±0.4 V; smaller matched devices improve it
without closing the 0.439-mV gate in the measured midrange case.

The complementary screen still uses **ideal** `STRACK`, ideal boosted
PMOS-gate tracking/hold steering, ideal `OFF_MAIN`/PHIB sources, and
idealized CDAC reference switches. Its PMOS body follows GMAIN only as
a dynamic-well feasibility hypothesis. Zero printed CMI in nominal runs
does not clear foundry reliability, well isolation, layout, PVT,
noise, dynamic aperture, input distortion, next-cycle acquisition,
reference settling, or ADC-level static/dynamic performance.

## Immediate design target

Keep the top-plate topology and `GMAIN→VIN` off strategy. Determine
whether the remaining input-dependent hold step is primarily control
edge timing, NMOS/PMOS sizing asymmetry, or device-to-top-node charge
injection, using one-factor Spectre tests. Then implement the boosted
`GMAIN` tracking path and PMOS gate steering with actual T28 devices
and a realizable 0.9-V-system control network. Do not freeze this
pass-device size, modify production OA, or claim sampling-block signoff
until raw error, acquisition, stress, and full-range tests pass.
