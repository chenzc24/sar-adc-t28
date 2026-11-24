"""Build the static site, current RNL workspace and versioned layout display."""

import argparse
import hashlib
import html
import json
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from string import Template
from urllib.parse import unquote, urlencode, urlsplit


SITE = Path(__file__).resolve().parent
ROOT = SITE.parent
REPOSITORY = "https://github.com/chenzc24/sar-adc-t28"
PAGES_URL = "https://chenzc24.github.io/sar-adc-t28/"
REVISION = "63c36806c5d7f612bb7e9ecafb4d3ce2da7a78cc"
SNAPSHOT = f"{REPOSITORY}/blob/{REVISION}"
PAGES = {
    "index": ("Overview", "An 8-bit, 10 MS/s asynchronous SAR ADC in TSMC 28 nm."),
    "architecture": ("Architecture", "The sampling, decision and feedback paths of the SAR ADC."),
    "schematic": ("Schematics", "Browse the current circuit hierarchy and Spectre sources in RNL Viewer."),
    "verification": ("Verification", "Post-layout measurements, limits and coverage for the SAR ADC."),
    "layout": ("Layout", "The routed ADC core, filled die, IO ring and physical verification."),
    "review": ("Design review", "Open design and verification items with their evidence and acceptance criteria."),
    "history": ("History", "The SAR ADC design revisions, experiments and historical measurements."),
}
FIGURES = {
    "assets/baseline-spectrum.png": "results/fft/ab_spectrum.png",
}
STATIC = ("assets/project.css", "assets/layout-view.css", "assets/layout-view.js")
LAYOUT_PART_SIZE = 192 * 1024
NATIVE_VIEWERS = {
    "0.3": "https://rich-netlist.github.io/rnl/viewer-0.3/",
    "0.4": "https://rich-netlist.github.io/rnl/viewer/",
}
SCHEMATIC_LEVELS = {
    "ADC core": "sar_adc8_join_r4",
    "Bootstrap": "sar_bootstrap_flat_8b_p",
    "CDAC": "sar8j_r1_cdac",
    "StrongARM": "sar_strongarm_t28",
    "SAR controller": "sar8_se_ctrl",
    "Reference drive": "sar8i_refword",
}
BLOCKS = {
    "bootstrap_n": ("Bootstrap N", "bootstrap", "bootstrap"),
    "bootstrap_p": ("Bootstrap P", "bootstrap", "bootstrap"),
    "cdac": ("MOM CDAC", "cdac", "cdac"),
    "comparator": ("StrongARM", "comparator", "comparator"),
    "reference": ("Reference drive", "reference", "reference"),
    "sar": ("SAR logic", "sar", "sar"),
}


def git_output(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def frozen_file(path):
    return git_output("show", f"{REVISION}:{path}")


def schematic_workspace(base_url):
    workspace = json.loads((ROOT / "design/rnl/workspace.json").read_text(encoding="utf-8"))
    design = json.loads((ROOT / "design/manifest.json").read_text(encoding="utf-8"))
    scheme, host, *_ = urlsplit(base_url)
    revision = git_output("rev-parse", "HEAD").decode().strip()
    workspace.update(
        base=f"{base_url}rnl/source/",
        level=design["top"],
        source={"repo": "chenzc24/sar-adc-t28", "commit": revision, "url": f"{REPOSITORY}/commit/{revision}"},
    )
    files = {}
    for item in workspace["files"]:
        relative = PurePosixPath(item["path"])
        if relative.parts[0] != "design" or ".." in relative.parts or relative.suffix not in {".scs", ".rnl"}:
            raise SystemExit(f"Invalid schematic workspace path {relative}")
        content = (ROOT / relative).read_bytes()
        if len(content) != item["size"] or hashlib.sha256(content).hexdigest() != item["sha256"]:
            raise SystemExit(f"Regenerate the native RNL workspace after changing {relative}")
        files[f"rnl/source/{relative}"] = content
    files["rnl/workspace.json"] = json.dumps(workspace, indent=2).encode()
    entry = files[f'rnl/source/{workspace["entry"]}']
    version = next((v for v in NATIVE_VIEWERS if f'@VERSION("{v}")'.encode() in entry), None)
    if version is None:
        raise SystemExit("The schematic has no supported RNL version in its header.")
    drawing = json.loads((ROOT / "design/rnl/manifest.json").read_text(encoding="utf-8"))
    dut = ROOT / "design/dut.scs"
    if hashlib.sha256(dut.read_bytes()).hexdigest() != drawing["source_hashes"]["design/dut.scs"]:
        raise SystemExit("Regenerate the native RNL workspace for the current DUT entry.")
    levels = drawing["levels"]
    if any(level not in levels for level in SCHEMATIC_LEVELS.values()):
        raise SystemExit("Check the site's schematic module links against the current hierarchy.")

    def url(level, embed=False):
        params = {"manifest": f"{base_url}rnl/workspace.json", "level": level, "lang": "en"}
        if embed:
            params.update(embed="1", origin=f"{scheme}://{host}")
        return html.escape(f"{NATIVE_VIEWERS[version]}?{urlencode(params)}", quote=True)

    links = "\n".join(f'<a href="{url(level, True)}" target="rnl-frame">{label}</a>'
                      for label, level in SCHEMATIC_LEVELS.items())
    return files, {
        "rnl_embed": url(design["top"], True),
        "rnl_full": url(design["top"]),
        "rnl_links": links,
        "rnl_version": version,
        "rnl_top": design["top"],
        "rnl_revision": revision[:7],
        "rnl_entry": f'rnl/source/{workspace["entry"]}',
    }


def floorplan():
    plan = json.loads(frozen_file("Layout/design/floorplan.json"))
    xmin, ymin, xmax, ymax = plan["core_bbox"]
    width, height = xmax - xmin, ymax - ymin
    regions = []
    for block in plan["blocks"]:
        label, anchor, theme = BLOCKS[block["id"]]
        x, y = block["origin"]
        w, h = block["size"]
        position = (
            f"--x:{100 * (x - xmin) / width:.4f}%;--y:{100 * (ymax - y - h) / height:.4f}%;"
            f"--w:{100 * w / width:.4f}%;--h:{100 * h / height:.4f}%"
        )
        regions.append(
            f'<a class="region region-{theme}" style="{position}" '
            f'href="architecture.html#{anchor}"><span>{label}</span></a>'
        )
    return "\n".join(regions)


def navigation(current):
    links = []
    for page, (label, _) in PAGES.items():
        active = ' aria-current="page"' if page == current else ""
        links.append(f'<a href="{page}.html"{active}>{label}</a>')
    return "\n".join(links)


def render_pages(schematic):
    layout = Template((SITE / "layout.html").read_text(encoding="utf-8"))
    context = {
        "repository": REPOSITORY,
        "snapshot": SNAPSHOT,
        "revision": REVISION,
        "short_revision": REVISION[:7],
        "floorplan": floorplan(),
        **schematic,
    }
    pages = {}
    for name, (label, description) in PAGES.items():
        article = Template((SITE / "pages" / f"{name}.html").read_text(encoding="utf-8"))
        pages[f"{name}.html"] = layout.substitute(
            context,
            title=html.escape(f"{label} · SAR ADC T28"),
            description=html.escape(description),
            navigation=navigation(name),
            content=article.substitute(context),
        )
    return pages


class PageLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.links = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if "id" in attributes:
            identifier = attributes["id"]
            if identifier in self.ids:
                raise ValueError(f"Duplicate ID {identifier}")
            self.ids.add(identifier)
        self.links.extend(attributes[key] for key in ("href", "src") if key in attributes)


def check_links(pages, assets):
    parsed = {}
    for name, markup in pages.items():
        parser = PageLinks()
        parser.feed(markup)
        parsed[name] = parser

    tracked = set(git_output("ls-tree", "-r", "--name-only", REVISION).decode().splitlines())
    errors = []
    for name, page in parsed.items():
        for link in page.links:
            target = urlsplit(link)
            if link.startswith(f"{SNAPSHOT}/"):
                source = unquote(target.path.split(f"/{REVISION}/", 1)[1])
                if source not in tracked:
                    errors.append(f"{name}: missing source {source}")
            elif not target.scheme and not target.netloc:
                path = str(PurePosixPath(unquote(target.path))) if target.path else name
                if path not in pages and path not in assets:
                    errors.append(f"{name}: missing local file {link}")
                elif target.fragment and path in parsed and unquote(target.fragment) not in parsed[path].ids:
                    errors.append(f"{name}: missing anchor {link}")
    if errors:
        raise SystemExit("\n".join(errors))


def layout_artifacts():
    release = json.loads((SITE / "layout-data/release.json").read_text(encoding="utf-8"))
    layout_record = json.loads((ROOT / "Layout/results/chip_fill.json").read_text(encoding="utf-8"))
    if release["source_sha256"] != layout_record["current"]["chip_stream"]["sha256"]:
        raise SystemExit("Regenerate the layout display for the current unfilled chip stream.")
    geometry = (SITE / "layout-data/chip.core.lml.gz").read_bytes()
    digest = hashlib.sha256(geometry).hexdigest()
    if digest != release["geometry_sha256"]:
        raise SystemExit("The layout geometry does not match its release metadata.")
    # Keep the original gzip stream intact and transfer its bytes in small, retryable parts.
    parts = {
        f"layout-data/chip-{digest[:12]}-{index:02}.bin": geometry[offset:offset + LAYOUT_PART_SIZE]
        for index, offset in enumerate(range(0, len(geometry), LAYOUT_PART_SIZE))
    }
    release["geometry_parts"] = list(parts)
    parts["layout-data/release.json"] = json.dumps(release, indent=2).encode()
    return parts


def build(output, base_url):
    schematic, context = schematic_workspace(base_url.rstrip("/") + "/")
    artifacts = {**schematic, **layout_artifacts()}
    pages = render_pages(context)
    check_links(pages, {*FIGURES, *STATIC, *artifacts})
    for name, content in pages.items():
        destination = output / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8", newline="\n")
    for filename, source in FIGURES.items():
        destination = output / filename
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(frozen_file(source))
    for name, content in artifacts.items():
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    for name in STATIC:
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SITE / name, path)
    print(f"Built {len(pages)} pages, the RNL workspace, and the layout viewer at {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist" / "site")
    parser.add_argument("--base-url", default=PAGES_URL)
    args = parser.parse_args()
    build(args.output.resolve(), args.base_url)
