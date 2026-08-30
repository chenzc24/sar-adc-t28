# T28 PDK Primitive Characterization

## Purpose

This is the first transistor/primitive bridge between the behavioral SAR ADC
budget and later block-level transistor design. The circuit topology is stored
as Virtuoso schematics; the numerical evidence comes from Spectre using the
PDK netlist emitted from those schematics.

This stage does not design the comparator, sampling switch, reference buffer,
or CDAC. It establishes verified device names, terminals, CDF controls, a
repeatable simulation path, and first-order sizing data.

## Verified PDK Surface

| Primitive | Symbol terminals | Parameters used |
| --- | --- | --- |
| `tsmcN28/nch_mac` | `B D G S` | `l`, `Wfg`, `fingers`, `simM` |
| `tsmcN28/pch_mac` | `B D G S` | `l`, `Wfg`, `fingers`, `simM` |
| `tsmcN28/cfmom_2t` | `MINUS PLUS` | `Wfinger`, `Sfinger`, `Lfinger`, `Nfinger`, `StartMn`, `StopMn` |

The MOS CDF exposes `nf` as a read-only derived value. The editable number of
fingers is `fingers`. The two-terminal `cfmom_2t` was selected for
characterization because both its terminal surface and capacitance callback
were verified. This is not yet a CDAC unit-capacitor selection.

## Virtuoso Testbenches

- `SAR_ADC_T28/tb_nmos_char/schematic`: `nch_mac` with independent `VGS` and
  `VDS` sources; source and body are on `gnd!`.
- `SAR_ADC_T28/tb_pmos_char/schematic`: `pch_mac` with independent `VDD`, gate,
  and drain sources; source and body are on `VDD`.
- `SAR_ADC_T28/tb_cap_char/schematic`: `cfmom_2t` driven by `VBIAS`, with the
  negative terminal on `gnd!`.

Bridge readback verified every instance, master, parameter, and connection.
Virtuoso then netlisted all three schematics successfully. The emitted netlist
contains the PDK-managed TT macro/MOS/MOM model sections; no PDK model text was
copied into the repository.

## First-Pass Conditions

- Process: nominal TT model path emitted by the PDK netlister
- Temperature: 27 C
- Core supply and MOS drain magnitude: 0.9 V
- MOS geometry: `Wfg=1 um`, `L=30 nm`, one finger, multiplier one
- Gate sweep: 0 to 0.9 V in 5 mV steps, 181 points
- MOM geometry: 50 nm finger/space, 4 um finger length, 32 fingers, M1-M3
- MOM AC sweep: 1 kHz to 10 GHz, 20 points/decade, 141 points

## Results

All three Spectre runs completed with zero errors. The repeated PDK warning is
the model deck redefining a scoped `scalefactor`; Spectre used the final value
and completed normally.

| Quantity | NMOS | PMOS |
| --- | ---: | ---: |
| `|Vth|` near full gate bias | 0.300 V | 0.331 V |
| `|Id|` at `|VGS|=|VDS|=0.9 V` | 728 uA/um | 615 uA/um |
| `gm` at full gate bias | 1.694 mS/um | 1.239 mS/um |

Representative `gm/Id` sizing points at `|VDS|=0.9 V` are:

| Device | `gm/Id` | Gate magnitude | `|Id|/W` | `gm/W` | Intrinsic gain |
| --- | ---: | ---: | ---: | ---: | ---: |
| NMOS | 19.84 1/V | 0.295 V | 8.50 uA/um | 0.169 mS/um | 12.21 V/V |
| NMOS | 14.99 1/V | 0.365 V | 28.66 uA/um | 0.430 mS/um | 12.37 V/V |
| NMOS | 9.95 1/V | 0.455 V | 86.34 uA/um | 0.859 mS/um | 12.46 V/V |
| PMOS | 19.99 1/V | 0.280 V | 7.10 uA/um | 0.142 mS/um | 6.68 V/V |
| PMOS | 14.91 1/V | 0.355 V | 26.26 uA/um | 0.392 mS/um | 6.78 V/V |
| PMOS | 10.03 1/V | 0.440 V | 74.65 uA/um | 0.749 mS/um | 6.82 V/V |

The MOM CDF reports 35.6304 fF. Spectre extracts 35.6355 fF at low frequency,
a 0.0143% difference, and the extracted capacitance remains effectively flat
through 10 GHz for this ideal two-terminal fixture. This agreement validates
the chosen PCell parameters and the AC extraction path.

The capacitor CDF remains at its PDK-default `mismatch=Model` setting, but this
run is a nominal AC analysis, not a Monte Carlo analysis. It therefore does
not apply or measure local mismatch.

## Design Meaning

The `gm/Id` lookup is now usable for initial bias-current and width estimates.
For example, near `gm/Id=15 1/V`, one micrometre of device width carries about
28.7 uA for NMOS and 26.3 uA for PMOS at this drain bias. Those values provide
a concrete starting point for comparator preamplifier or reference-buffer
sizing.

The short-channel intrinsic gain is modest: about 12 V/V for NMOS and 6.7 V/V
for PMOS in this fixture. A block that needs high open-loop gain cannot assume
minimum-length devices are sufficient; longer channel lengths, gain boosting,
cascoding, or regenerative operation must be evaluated at the block level.

The 35.6 fF MOM is only a deliberately measurable characterization specimen.
Choosing a SAR CDAC unit requires a separate tradeoff across total sampling
capacitance, matching, DNL/INL yield, switching energy, reference settling,
parasitics, and area. It must not be treated as the selected unit capacitor.

## Current Limits And Next Iteration

This baseline covers one geometry, TT, 27 C, zero body bias, and a single high
drain bias. It does not yet include output-characteristic sweeps, channel-length
sweeps, body effect, flicker/thermal noise, Monte Carlo mismatch, SS/FF,
voltage/temperature extremes, extracted parasitics, or capacitor matching.

The next characterization increment should add length and drain-bias sweeps,
then verified PVT corners and noise. Only after those data are available should
the first comparator, sampling-switch, and CDAC transistor-level sizing be
frozen.

## Reproduction

Run the scripts in order from the repository root:

```powershell
uv run --project ..\..\virtuoso-bridge-lite python scripts\characterization\audit_pdk_primitives.py --output output\pdk_characterization\pdk_inventory.json
uv run --project ..\..\virtuoso-bridge-lite python scripts\characterization\create_testbenches.py --output output\pdk_characterization\schematic_readback.json
$env:VB_DISABLE_CONTROL_MASTER='1'
uv run --project ..\..\virtuoso-bridge-lite python scripts\characterization\export_testbenches.py
uv run --project ..\..\virtuoso-bridge-lite python scripts\characterization\run_characterization.py
uv run --project ..\..\virtuoso-bridge-lite --with matplotlib python scripts\characterization\analyze_characterization.py
```

`create_testbenches.py` intentionally refuses to overwrite existing cells.
Generated netlists, PSF, CSV, JSON, and plots remain under the ignored
`output/pdk_characterization/` tree.
