# Project website

Build from the repository root with Python 3.11 or newer and Git on PATH. Pass the extracted [RNL 0.5.7 upgrader](https://github.com/rich-netlist/rnl/releases/tag/core-v0.5.7) and [RNL 0.6.1 checker](https://github.com/rich-netlist/rnl/releases/tag/core-v0.6.1).

```sh
python site/build.py --rnl-upgrader /path/to/0.5.7/rnl --rnl-checker /path/to/0.6.1/rnl
```

Serve `dist/site` over HTTP to preview the site and its layout data. `--output` selects another build directory and `--base-url` sets the absolute host and path for the RNL workspace.

The deployment workflow checks site changes in pull requests and publishes the build on every push to `main`. The repository's Pages source is GitHub Actions. [Project website](https://chenzc24.github.io/sar-adc-t28/) · [Deployment workflow](../.github/workflows/project-site.yml)

The build upgrades the hash-bound current Spectre drawing to RNL 0.4, checks the result and publishes it with a manifest for the [current official viewer](https://rich-netlist.github.io/rnl/viewer/). The upgrade runs on a copy and verifies that every Spectre statement is preserved. Run `python -m tools.saradc draw` after changing the DUT or its authored drawing records. The [RNL guide](../docs/schematics/README.md) describes the local editing service.

The layout page loads LayoutML's published `virtuoso_tsmc28` renderer. To refresh its data, run `python site/export_layout.py <unfilled-gds>` with `gdstk` installed. The exporter validates the recorded r8 stream and preserves hierarchy, routing, instantiated transistor geometry, source/drain labels, vias and bond-pad metal. D/S labels come from GDS text purpose 127/0. The display omits density fill and shows standard-cell and IO library outlines. [LayoutML Studio](https://liixtt.github.io/LayoutML/lml_renderer.html#style=virtuoso_tsmc28) · [Physical evidence](../Layout/results/chip_fill.md)

English pages live in `pages/` and Simplified Chinese pages in `pages/zh/`. Keep the corresponding section IDs aligned for language switching. Architecture belongs on Overview. Current measurements and open checks belong on Verification, and previous revisions belong on History. Update the pinned evidence commit when publishing a new snapshot. [Engineering results](../results/README.md)
