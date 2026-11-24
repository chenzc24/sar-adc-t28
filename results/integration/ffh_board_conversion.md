# Board-input to board-output conversion at FF hot

**Passed.** The output register captured each ADC result on the next rising edge of its local clock, CK_REG. Core D immediately before the edge, register Q, the on-chip pad and the modeled board pin agreed. Board settling starts at the 50% crossing of CK_REG and ends at the first saved point that stays within the engineering logic thresholds for the rest of the observed interval.

| Conversion | Differential input | Core D / Q / pad / board | Board settling |
| --- | ---: | --- | ---: |
| Warmup | −0.896484375 V | 0x00 / 0x00 / 0x00 / 0x00 | 1.853 ns |
| Scored | +0.896484375 V | 0xFF / 0xFF / 0xFF / 0xFF | **2.046 ns** |

The 10 MS/s Spectre run used FF devices at 125 °C, 0.99 V core and 1.98 V IO. Each 50 Ω input source drove the modeled bond and PDB3AC pad into the Stage 6 fill5 extracted ADC. The output path included the register, drivers, pads, 0.2 Ω and 2 nH per bond and 15 pF per board output. The peripheral routing used unfilled r3 typical RC with the measured r8/fill7 VIN and VREF capacitance increments. Board logic thresholds were 0.594 V and 1.386 V. This endpoint check covers normal operation for these package and receiver assumptions. [Peripheral extraction](../../Layout/results/chip_periphery.json) · [Fill capacitance measurements](../../Layout/results/chip_fill.md)

Managed run `sar8-handoff-ffh-joint-io-a` completed on `thu-song`. The trace contains 61,401 saved samples over 307 ns. The collected result SHA-256 is `a48e7c018cc9be5afe5e94dece7fc0e7b95941ac4ac9bf3b456d9e39434d16f2`. [Native measurements](ffh_board_conversion.json)
