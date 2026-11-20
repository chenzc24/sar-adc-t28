# Specifications and Test Definitions

- System architecture, complete port order, sampling and conversion, device implementations, loads, targets, error budgets, calibration open items, verification scope, and behavioral parameters. [Machine-readable design specification](arch.json)
- Readable specification generated from the design source. [Design specification](../docs/specification.md)
- Five established corners. The frozen deck identifies the exact device sections. [Corner definitions](corners.json)
- A 45-point MOS, supply, and temperature matrix, run for the reset-OR design. Reuse the original five and test ten frames at each of the 40 additional points. Passives use TT. [PVT short-test matrix](pvt_short.json)
- The per-device engineering screen for terminal voltages, including the transient over-limit window and evidence requirements. Use PDK-supported evidence for lifetime qualification. [Terminal-voltage rule](soa_rule.yaml)
- Module masters, port order, and implementation paths. [Block specifications](blocks/)
- Input digests, analyzers, budgets, and historical run identities for seven real templates. [Test registry](tests.json)
- Scope of the 200-seed module tests and the two 50-seed cold-corner tests. [Monte Carlo scope](monte_carlo.json)
- Named views and Verilog-A or transistor selection for each of five modules. [View registry](views.json)
- Physical candidates, defaults, and public interfaces. Internal helper circuits may differ. [Candidate registry](candidates.json)
- Stimulus, loads, measurements, diagnostic limits, and coverage gaps for the five standalone block tests. [Block test registry](block_tests.json)

Treat blank values as undefined or unverified. Use measurement evidence for qualification. Establish a same-draw Monte Carlo comparison from the seed and the statistical model and input identities.

The current design, `sar8_single_edge_bitwise_v1`, uses `sar=single_edge` and `reference=single_edge_d2`, with the other modules from B, and a 45 ns high / 55 ns low external clock. The adoption record includes exact file digests, run identities and the scope of each run. Continue to apply the terminal-voltage rule. B's 16-capture contract, 40 ns sampling phase, behavioral timing, and historical performance evidence belong to the B configuration. [Adoption record](../results/design/sar_single_edge_adoption_20261120.json) · [Terminal-voltage rule](soa_rule.yaml)
