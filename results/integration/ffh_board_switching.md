# Eight-bit simultaneous switching at the board load

**Passed.** The bench drove the Core D interface across each capture edge. The extracted output routes, physical register, clock receiver and output drivers delivered each word to the pad and the modeled board pin. Both carry transitions switched all eight bits.

| Captured word | Q / pad / board | Board settling after CK_REG rises |
| --- | --- | ---: |
| 0x7F, initial capture | 0x7F / 0x7F / 0x7F | 1.844 ns |
| 0x80 | 0x80 / 0x80 / 0x80 | 1.899 ns |
| 0x7F | 0x7F / 0x7F / 0x7F | **2.023 ns** |

The FF-hot fixture used 125 °C, 0.99 V core, 1.98 V IO, the r3 extracted peripheral routes and a 0.2 Ω, 2 nH bond feeding 15 pF per output. The board word had to stay valid at the 0.594 V and 1.386 V engineering thresholds. The shortest interval from settling to the next CK_REG falling edge was 42.919 ns. Actual receiver timing depends on the board sampling edge and input thresholds. The companion conversion run exercises the ADC that supplies Core D in operation. [Board-to-board conversion](ffh_board_conversion.md)

Managed run `sar8-handoff-ffh-board-ss8-b` completed on `thu-ming`. The trace contains 54,001 saved samples over 270 ns. The collected result SHA-256 is `9ddfae70451d152cac4f480c59e3e15cd0d51847905ca17fadf43a24588aea45`. [Native measurements](ffh_board_switching.json)
