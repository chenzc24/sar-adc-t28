# Second comparison on retained charge

Local proposal: `sar8audit-comp-hold2-tt-v1`. No remote submission or baseline
adoption was performed.

The sole electrical change from kickback_v2 is removal of the44--58.1ns CINIT
pulse in both arms. Inputs remain disconnected from their initialization sources
from18.1ns until84ns. Comparisons still start at20ns and60ns, both with the
original+0.25LSB nominal target. All other cycles, devices, sources, models,
references, numerical settings, endpoints, analyzer and budgets are unchanged.

Measurement metadata identifies18.1ns as the actual release origin for compare2;
it does not claim another release at58.1ns. The next actual acquisition after
compare1 is84ns. The32.1--84ns interval includes compare2 and must not be treated
as a reset-only phase in later reports.

After parent managed execution, read result.json `cycles[1]`: `pre_compare`
contains the retained differential/common-mode voltages,
`pre_compare_target_error_v` measures residual versus the original target, and
`writes`, `write_delay_from_clock_half_s` and `late_D0_bit` describe the second
accepted decision. Compare those directly with frozen kickback_v2 cycle2.

Three local single-variable checks passed, including all other statements and
payload bytes unchanged, initialization-source difference confined to the
omitted pulse, and a synthetic actual-config probe that exposes a deliberately
supplied residual before compare2. Exact81 save symbols remain validated.
No physical result is claimed for this new package.
