# Project website

Run `python site/build.py` from the repository root with Python 3.11 or newer and Git on PATH. Serve `dist/site` over HTTP to preview the site and its layout data. `--output` selects another build directory and `--base-url` sets the absolute host and path for the RNL workspace.

The deployment workflow checks site changes in pull requests and publishes the build on every push to `main`. The repository's Pages source is GitHub Actions. [Project website](https://chenzc24.github.io/sar-adc-t28/) · [Deployment workflow](../.github/workflows/project-site.yml)

The build packages the current hash-bound RNL workspace for the official viewer. Run `python -m tools.saradc draw` after changing the DUT or its authored drawing records. The [RNL guide](../docs/schematics/README.md) describes the local editing service. On the deployed site, the viewer loads the workspace through its manifest URL.

The layout page reads the compressed LayoutML Core data in `layout-data/`. To refresh it, run `python site/export_layout.py <unfilled-gds>` in a Python environment with `gdstk` installed. The exporter checks the GDS digest and die extent against the unfilled stream recorded in `Layout/results/chip_fill.json`. It keeps the project-owned drawing polygons and instance transforms, omits density fill, and represents external library cells by their bounds. The source GDS is stored with the physical evidence. [Physical evidence](../Layout/results/chip_fill.md)

Page copy lives in `pages/`. Update the pinned evidence commit and the Verification and History copy together when publishing a new evidence snapshot. Keep earlier measurements associated with their own DUT and run conditions. [Engineering results](../results/README.md)
