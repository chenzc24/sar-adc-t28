# Show final ADC codes as a classical sine staircase

## Goal, ownership and dependencies

User wants an intuitive staircase relating final ADC codes to the source sine.
Add a saved-data plot to Result section6. Use the same500kHz R3+B1um record
already cited there; do not promote new candidate/acceptance work into it.
Remote OA owned:none. No simulation, circuit, UI or source-data changes.

At start Result and prior final-figure generator are clean. User Wrap-up,
other moved/draft notes, new pasted image, b_short_acceptance source/analyzer
and cdac10_dualrail work are dirty/untracked and excluded. Read AGENTS, README,
current Result and the original B sampling/read-time definition.

Owned: Obsidian_docs/Rvision/Result.md; new assets/result8_staircase/ PNG,SVG,
manifest/source note; scripts/reporting/result8_staircase.py; this plan and
one factual append to plan/log.md. All prior figures/generators, other notes,
simulation data and unrelated experiments remain read-only.

Starting commit1fe7174. Concurrent docs/b_short_acceptance.md later appeared;
it is also outside this plot-only target and remains untracked/untouched.

## Display and checks

Map measured final codes to bin-center input voltage:
V=-0.9+(code+0.5)*(1.8/256). Overlay the saved source sine and the staircase;
show sample-aligned reconstruction first and conservative actual98ns read-time
alignment separately. State zero-order hold is a display convention for read
samples, not the internal working register or a new analog-output circuit.
Use the preceding warm-up code to cover the start of the displayed2us window.
Retain bench/module headers. Keep the raw-error result available as a folded
detail, not a replaced acceptance test.

Compile/run the plotting script, verify input/result/receipt hashes,24final
codes and mapping round-trip,20observed samples,100ns spacing and56.95ns read
delay. Visually inspect PNG, parse SVG/XML, check embed/YAML and unchanged
summary metrics. Scoped diff-check/review, log and local commit:
docs: show ADC sine as voltage-code staircase. No push requested.

## Outcome

Added a two-panel classic sine/staircase plot with dual voltage/code axes.
Both panels use the same20 measured final codes: sample-time alignment first,
actual98ns read-time alignment second. Prior warm-up frame3 supplies the first
interval. Bin-center reconstruction and display-only ZOH are explicit; no
claim of an added held hardware output bank or physical reconstruction DAC.
Original raw-error figure is folded below, metrics unchanged.

Script compile/execution, all24 final-code reads from saved D pins, inverse
mapping,100ns sample spacing,56.95ns read delay,20 observed samples and data/
figure hashes pass. PNG visually inspected, SVG/XML and Markdown/YAML/link
checks pass; scoped diff-check clean. No new experiment, OA or GUI changes.
Other user/concurrent work remains excluded. Local scoped commit only.
