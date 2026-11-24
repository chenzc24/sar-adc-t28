# Project website

Run `python site/build.py` from the repository root with Python 3.11 or newer and Git on PATH. Open `dist/site/index.html` in a browser. `--output` selects another build directory. The output can be served by any static web host.

The deployment workflow checks site changes in pull requests and publishes the build on every push to `main`. The repository's Pages source is GitHub Actions. [Project website](https://chenzc24.github.io/sar-adc-t28/) · [Deployment workflow](../.github/workflows/project-site.yml)

The five pages cover the architecture, verification, layout and open review items. Page copy lives in `pages/`. The build reuses the project floorplan coordinates, embedded schematic hierarchy and evidence figures at the commit in `build.py`. It checks local links and anchors and verifies that pinned GitHub file links resolve to paths in that commit. The [RNL guide](../docs/schematics/README.md) describes the local editing service.

Update the pinned commit and review the claims and links in the page copy together when publishing a new evidence snapshot. Keep earlier measurements associated with their own DUT and run conditions. [Engineering results](../results/README.md)
