"""Build the static project site from a pinned engineering snapshot."""

import argparse
import html
import json
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from string import Template
from urllib.parse import unquote, urlsplit


SITE = Path(__file__).resolve().parent
ROOT = SITE.parent
REPOSITORY = "https://github.com/chenzc24/sar-adc-t28"
REVISION = "63c36806c5d7f612bb7e9ecafb4d3ce2da7a78cc"
SNAPSHOT = f"{REPOSITORY}/blob/{REVISION}"
PAGES = {
    "index": ("Overview", "An 8-bit, 10 MS/s asynchronous SAR ADC in TSMC 28 nm."),
    "architecture": ("Architecture", "The sampling, decision and feedback paths of the SAR ADC."),
    "verification": ("Verification", "Post-layout measurements, limits and coverage for the SAR ADC."),
    "layout": ("Layout", "The routed ADC core, filled die, IO ring and physical verification."),
    "review": ("Design review", "Open design and verification items with their evidence and acceptance criteria."),
}
SCHEMATIC = "schematic.html"
FIGURES = {
    "assets/io-ring.png": "Layout/results/io_ring.png",
    "assets/cdac-fill.png": "Layout/results/figures/cdac_planned_fill.png",
    "assets/sar-routing.png": "Layout/results/figures/sar_se_core.png",
    "assets/baseline-spectrum.png": "results/fft/ab_spectrum.png",
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


def static_schematic():
    viewer = frozen_file("docs/schematics/index.html")
    native_mode = b"nativeMode=location.protocol!=='file:'"
    mode_button = b'<button id="mode">'
    if viewer.count(native_mode) != 2 or viewer.count(mode_button) != 1:
        raise SystemExit("Review the static schematic adapter for the pinned viewer revision.")
    # The bundled SVGs work on a static host. The native viewer requires draw --serve.
    return viewer.replace(native_mode, b"nativeMode=false").replace(
        mode_button, b'<button id="mode" hidden>'
    )


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


def render_pages():
    layout = Template((SITE / "layout.html").read_text(encoding="utf-8"))
    context = {
        "repository": REPOSITORY,
        "snapshot": SNAPSHOT,
        "revision": REVISION,
        "short_revision": REVISION[:7],
        "floorplan": floorplan(),
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


def build(output):
    pages = render_pages()
    css = "assets/project.css"
    check_links(pages, {*FIGURES, css, SCHEMATIC})
    schematic = static_schematic()
    for name, content in pages.items():
        destination = output / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8", newline="\n")
    for filename, source in FIGURES.items():
        destination = output / filename
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(frozen_file(source))
    (output / SCHEMATIC).write_bytes(schematic)
    shutil.copyfile(SITE / css, output / css)
    print(f"Built {len(pages)} pages and the schematic viewer at {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist" / "site")
    build(parser.parse_args().output.resolve())
