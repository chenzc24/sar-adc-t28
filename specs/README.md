# Specifications and Test Definitions

- System architecture, complete port order, sampling and conversion, device implementations, loads, targets, error budgets, calibration open items, verification scope, and behavioral parameters. [Machine-readable design specification](arch.json)
- Readable specification generated from the design source. [Design specification](../docs/specification.md)
- Five established corners. The frozen deck identifies the exact device sections. [Corner definitions](corners.json)
- A 45-point MOS, supply, and temperature matrix. Reuse the original five and test ten frames at each of the 40 additional points. Passives use TT. [PVT short-test matrix](pvt_short.json)
- The per-device engineering screen for terminal voltages, including the transient over-limit window and evidence requirements. Use PDK-supported evidence for lifetime qualification. [Terminal-voltage rule](soa_rule.yaml)
- Module masters, port order, and implementation paths. [Block specifications](blocks/)
- Input digests, analyzers, budgets, and historical run identities for seven real templates. [Test registry](tests.json)
- Scope of the 200-seed module tests and the two 50-seed cold-corner tests. [Monte Carlo scope](monte_carlo.json)
- Named views and Verilog-A or transistor selection for each of six modules. The RC and clear models preserve separate rise and fall delays and their characterization sources. [View registry](views.json)
- Physical candidates, defaults, and public interfaces. Internal helper circuits may differ. [Candidate registry](candidates.json)
- Stimulus, loads, measurements, diagnostic limits, and coverage gaps for the six standalone block tests. [Block test registry](block_tests.json)

Treat blank values as undefined or unverified. Use measurement evidence for qualification. Establish a same-draw Monte Carlo comparison from the seed and the statistical model and input identities.

The current design uses `reference=minimal_msb_d2` and `sar=reset_data_or`, with the other modules from B. The adoption record includes exact file digests and the scope of the FF-cold short test. Other corners were pending at that checkpoint. Continue to apply the terminal-voltage rule. B's 16-capture contract, behavioral timing, and historical performance evidence belong to the B configuration. [Adoption record](../results/design/reset_data_or_adoption_20261115.json) · [Terminal-voltage rule](soa_rule.yaml)
