# Compact sampling startup diagnosis

Local preparation only: not Spectre compiled, submitted or qualified.
The larger draft in the parent directory is retained and is not approved to run.

The fixture contains591 source primitives:237MOS,32MOM,322PDK resistor segments.
It retains both full Bootstrap circuits, the complete flat CDAC/pass switches,
reference final CP/CN stages and their gate resistors, the N4 reset comparator,
rx2 buffers and immediate PR/NR logic loads. Parameters come unchanged from the
frozen rx2 TT source; these decks select SS/0.81V/125C with TT passives.

The actual direct clock path is retained:

`SAMPLE -> XSAMPLE -> XIDLE.XA/XB -> XSEQ.XD/XA/XB -> SEQ_SAMPLE`

XIDLE.XA receives SAMPLE_INT on both inputs; this path does not need ACTIVE,
IDLE_D or the PRESET generator. SAMPLE_INT direct loading is completed with20
original two-MOS inverter cells. Their downstream loads are removed and listed
in boundary_loads.json: direct input terminal identity is preserved, but changed
output movement can change Miller loading. This is a declared approximation,
not proof of the integrated clock's exact transient behavior.

Verified direct terminal counts:

| Node | Source/retained terminals |
| --- | ---: |
| SAMPLE | 2/2 |
| SAMPLE_INT | 46/46 |
| SAMPLE_AND | 4/4 |
| SAMPLE_MATCH | 8/8 |
| QUAL | 4/4 |
| SEQ_SAMPLE | 10/10 |
| TOPP/TOPN | 12/12 each |
| COMP_P/COMP_N | 8/8 each |
| PR/NR | 8/8 each |

The reference oracle is called with symbolic reset events, giving Q=128:
BP0..6=.9V/BP7=0V, BN0..6=0V/BN7=.9V, fixed dummy P=.9V/N=0V.
Only undriven B inputs of the retained reference final inverters receive ideal
logic levels. Reference outputs, CDAC bottoms and Bootstrap internal nodes are
not clamped. Dynamic reference sequencing is outside this attachment.

CMP_CLK is exposed as CMP_RESET after the controller and its drivers have been
excluded; it is held at0V to retain the actual comparator reset input load.
RAW/DATA downstream receiver loads are cut and separately listed. No token
register, bit register, request loop or asynchronous SAR loop is retained.

short_low_history.scs and long_low_history.scs differ only in VSAMPLE prehistory.
The common source begins rising at101ns and falling at141ns, with100ps edges
and the original100ns period. Input PWL and50ohm sources, reference sources and
50ohm/4pF networks are copied verbatim. Short-low starts high then provides a
100ps low plateau; long-low begins low in DC. These names do not imply a pure
zero-precharge historical failure reproduction or that100ps is insufficient.

The real clock may filter the short low pulse. Observe every SAMPLE_INT,
SAMPLE_MATCH, QUAL and SEQ_SAMPLE crossing. If no actual SEQ_SAMPLE opening is
observed, record acquisition duration and normal-sampling pass as unknown.
Never move the source closing edge or the read time to manufacture a pass.
Historical diagnostic held read is141.8ns and the source differential target is
-.81V; verify actual close precedes the read. Preclose is measured0.2ns before
the observed SEQ_SAMPLE half-level falling crossing. Record Cboot, G−Vin and
both top voltages; branch saves include all Bootstrap MOS terminals.

Droop and startup budgets remain null. Static .25LSB remains a shared diagnostic
guard, not a new separate module allocation. No power-ramp case exists here.

Local validation:13 tests passed, including missing-load/extra-driver negative
cases, source/parameter identity, Q128 truth, common formal source, direct clock
fanout, old-draft SHA and byte-for-byte regeneration. The builder emits a compact
parameter-hash mapping instead of copying geometry into the boundary inventory.

Recheck locally from the parent sampling directory with:

```powershell
E:/bridge-Agent-T28/projects/sar-adc-t28/.venv/Scripts/python.exe -B -m unittest test_compact_builder -v
E:/bridge-Agent-T28/projects/sar-adc-t28/.venv/Scripts/python.exe -B compact_builder.py --check
```
