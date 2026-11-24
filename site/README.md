# Project website

Build from the repository root with Python 3.11 or newer and Git on PATH. Pass the extracted [RNL 0.5.7 upgrader](https://github.com/rich-netlist/rnl/releases/tag/core-v0.5.7) and [RNL 0.6.1 checker](https://github.com/rich-netlist/rnl/releases/tag/core-v0.6.1).

```sh
python site/build.py --rnl-upgrader /path/to/0.5.7/rnl --rnl-checker /path/to/0.6.1/rnl
```

Serve `dist/site` over HTTP to preview the site and its layout data. `--output` selects another build directory and `--base-url` sets the absolute host and path for the RNL workspace.

The deployment workflow checks site changes in pull requests and publishes the build on every push to `main`. The repository's Pages source is GitHub Actions. [Project website](https://chenzc24.github.io/sar-adc-t28/) · [Deployment workflow](../.github/workflows/project-site.yml)

The build upgrades the hash-bound current Spectre drawing to RNL 0.4, checks the result and publishes it with a manifest for the [current official viewer](https://rich-netlist.github.io/rnl/viewer/). The upgrade runs on a copy and verifies that every Spectre statement is preserved. Run `python -m tools.saradc draw` after changing the DUT or its authored drawing records. The [RNL guide](../docs/schematics/README.md) describes the local editing service.

The layout page loads LayoutML's published rendering module and selects `virtuoso_tsmc28`. The renderer applies the N28 DRF packets to the viewport geometry and its outline style to layers outside the pack, including M9 and VIA8. The site build splits the compressed LayoutML Core data into individually retryable parts. To refresh it, run `python site/export_layout.py <unfilled-gds>` with `gdstk` installed. The exporter checks the digest and die extent against the unfilled stream recorded in `Layout/results/chip_fill.json`. It preserves hierarchy, project-owned routing and pin purposes, generated route vias and bond-pad metal. It omits density fill and represents other library cells by their bounds. [LayoutML Studio](https://liixtt.github.io/LayoutML/lml_renderer.html#style=virtuoso_tsmc28) · [Physical evidence](../Layout/results/chip_fill.md)

Page copy lives in `pages/`. Update the pinned evidence commit and the Verification and History copy together when publishing a new evidence snapshot. Keep earlier measurements associated with their own DUT and run conditions. [Engineering results](../results/README.md)
