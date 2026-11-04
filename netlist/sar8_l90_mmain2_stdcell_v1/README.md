# Mmain2/L90 + independent digital standard-cell candidate

Parent: byte-frozen historical `e94e802`, [manifest](../sar8_l90_mmain2_frozen/manifest.json).
Candidate SHA256: `f31b66c8fb35003bf7e8ad1a23d9c230b39f1f9651ccc469953e5e52ecf493ea`.
The earlier standard-cell candidate was based on a later stress-diagnostic DUT;
this candidate reapplies only its digital transformation onto the historical DUT.

Replaced native logic: INV/NAND, resettable DFF, clock buffers, and96 ordinary
reference-driver inverter pairs. Composed AND/OR/MUX/XOR/SR and RC internal INV
use these mapped primitives. Native library: `tcbn28hpcplusbwp12t30p140`, original
INVD1/ND2D1/DFCNQD1 SPICE. Include library_include.scs before dut.scs in a future
Spectre testbench; verify installed library identity from manifest before running.
Foundry files are referenced, not copied or modified.

Preserved: Mmain2, reference L90, Bootstrap/CDAC/comparator, all other subcircuits,
reference resistors, RC/clear and external SR load. Private parasitic/load capacitors
inside removed custom gates leave with that implementation; no hidden library
nodes are edited. Original reset polarity/handshake connectivity retained.
Supply/reference/clock test conditions are not altered by this netlist preparation.

Validation:12 changed master definitions,96 inverter pairs, same subcircuit ports,
unchanged other blocks and reference non-MOS elements; reversing replacements
recovers parent text exactly. These structural checks do not prove timing or ADC
performance equivalence. D1 is an initial drive choice, not a validated load choice.

**Not simulated or adopted.** Earlier standard-cell storage FF/SS tests support
bounded functional behavior only; whole ADC on this parent remains untested.
Standard-cell FF internal-node stress remains known and deferred in this task.
Actual internal sampling edge, handshake ordering, BBM, settling and power must
be measured; unchanged external clock does not guarantee unchanged aperture.

Next: paired TT short test (low/mid/high codes, startup separately) using exactly
the frozen parent's stimulus/load; then full-code and FFT if functional checks
pass. Existing original-parent TT finite batch continues unchanged. Preserve both
versions to attribute any performance change to this migration. No Git merge,
commit/push, OA edit, or automatic qualification was performed.
