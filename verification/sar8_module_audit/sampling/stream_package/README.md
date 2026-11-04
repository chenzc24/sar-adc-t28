# Local native-stream package

Prepared for parent review only. No recipe was written outside this subtree,
registered or submitted, and no simulator/compiler was invoked by this task.

Suggested run IDs in recipe_suggestions.json:

- sar8audit-sample-v2-short
- sar8audit-sample-v2-long

Each suggestion lists exact shared input files and its own measurement-only
test.scs. fixture_dut.scs is byte-identical to compact_v2. The deck only adds
case-correct native branch saves; devices, sources and time schedule are unchanged.
The original stream.cpp is copied byte-for-byte from the frozen loaded candidate;
loaded_remote.py is referenced from its existing shared path without editing it.
Their source paths and SHA are fixed in package_manifest.json.

Mapping covers all237MOS/six terminal pairs:1422 records deduplicated into581
node pairs. All native points contribute to stress extrema. Seven native
half-VDD event streams retain SAMPLE, SAMPLE_INT, SAMPLE_AND, SAMPLE_MATCH,
QUAL, SEQ_SAMPLE and CMP_RESET crossings. No synthetic opening is added.

The293 selected traces include input source/pin voltages, both tops, the actual
clock path, both Bootstrap G/BTOP/BBOT/CTRL/GRESET/CLKSB nodes,16CDAC bottoms,
Bootstrap MOS/Cboot terminal currents, reference pass-MOS terminal currents,
reference source/resistor/decap currents and supply/input/clock currents.

Products use every native interval for supply/reference/input/clock V*I. The
0–100ns bin is100ns long;100–160ns is only60ns and must not be treated as a
complete frame when converting energy to average power.

The reused parser holds one native sample, with20ps compact export spacing.
Configured analysis RSS limit is256MiB and collection ceiling is32MiB. The
compact binary upper bound is18823056bytes; an additional4194304bytes is reserved
for logs, metadata, failing pairs and derived tables. These are configured and
structural bounds; new-run native RSS has not yet been measured.

After parent-managed collection, review analog observations and events locally:

```powershell
E:/bridge-Agent-T28/projects/sar-adc-t28/.venv/Scripts/python.exe -B review_stream.py <collected-derived-directory> --mapping stream_package/common/mapping.json
```

Run from the parent sampling directory. The reader uses a memory map and emits
JSON to stdout. Stress/clock events remain native-point results; held/preclose
voltages are explicitly20ps compact-interpolation estimates. It preserves:

- Complete native crossing lists and DC clock levels for short-pulse filtering.
- Actual opening/closing and acquisition duration only when observed.
- Raw141.8ns top differential/source error even if its sampling meaning is invalid.
- A separate flag verifying141.8ns follows actual close; otherwise sampled held
  error remains null.
- Preclose error at actual close minus0.2ns and net turnoff change separately.
- Main gate-minus-input and Cboot top-minus-bottom values at the held observation.

The reference and comparator are fixed-state diagnostic attachments. There is
no conversion code, ADC accuracy qualification, power-ramp case, independent
droop budget or startup pass assigned by this reducer.

Local checks:9 tests pass, including all-MOS pair coverage, case-correct saves,
source SHA, suggestions/resource limits and four event scenarios: normal open/
close, filtered short pulse, absent close, close later than141.8ns. Package
generation is byte-for-byte reproducible and preserves old compact_v2 files.
