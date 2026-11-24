"""Build the static site, current RNL workspace and versioned layout display."""

import argparse
import hashlib
import html
import json
import posixpath
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from string import Template
from urllib.parse import unquote, urlencode, urlsplit

from schematic_rnl import convert


SITE = Path(__file__).resolve().parent
ROOT = SITE.parent
REPOSITORY = "https://github.com/chenzc24/sar-adc-t28"
PAGES_URL = "https://chenzc24.github.io/sar-adc-t28/"
REVISION = "eb75b017230ad150ea4b2f5f8c0d6612f8e20c01"
SNAPSHOT = f"{REPOSITORY}/blob/{REVISION}"
PAGES = {
    "en": {
        "index": ("Overview", "An 8-bit, 10 MS/s asynchronous SAR ADC in TSMC 28 nm."),
        "schematic": ("Schematics", "Browse the current circuit hierarchy in RNL Viewer."),
        "layout": ("Layout", "Inspect the unfilled r8 die from the IO ring to individual devices."),
        "verification": ("Verification", "Post-layout results, limits and open checks."),
        "history": ("History", "The SAR ADC design revisions and historical measurements."),
        "report": ("Report", "Design history from behavioral model to extracted ADC, including layout revisions, IO, fill and open verification."),
    },
    "zh-CN": {
        "index": ("概览", "TSMC 28 nm 工艺的 8 位、10 MS/s 异步 SAR ADC。"),
        "schematic": ("原理图", "用 RNL Viewer 查看当前电路与模块层次。"),
        "layout": ("版图", "查看 r8 无填充版图，从 IO 环放大到单个晶体管。"),
        "verification": ("验证", "后仿结果、指标和待完成的验证。"),
        "history": ("迭代", "ADC 的设计变更与历史测量。"),
        "report": ("阶段报告", "从行为模型到整片提取，回看采样器、SAR、CDAC、IO 与填充的返工及未收口事项。"),
    },
}
REDIRECTS = {"architecture": ("index", "architecture"), "review": ("verification", "electrical-checks")}
FIGURES = {
    "assets/baseline-spectrum.png": "results/fft/ab_spectrum.png",
    "assets/report-rc.png": "Layout/results/figures/sar_timing_compact.png",
    "assets/report-sar.png": "Layout/results/figures/sar_se_core.png",
    "assets/report-cdac.png": "Layout/results/figures/cdac_paired_comparison.png",
    "assets/report-small-bits.png": "Layout/results/figures/cdac_small_bit_center.png",
}
STATIC = ("assets/project.css", "assets/layout-view.css", "assets/layout-view.js",
          "assets/schematic-view.js", "assets/language.js",
          "assets/report-comparator.png", "assets/report-chip.png", "assets/report-ff-stress.png")
LAYOUT_PART_SIZE = 192 * 1024
RNL_VIEWER = "https://rich-netlist.github.io/rnl/viewer/"
RNL_ENTRY = "design/rnl/export.scs"
SCHEMATIC_LEVELS = {
    "sar_adc8_join_r4": ("ADC core", "ADC 核心"),
    "sar_bootstrap_flat_8b_p": ("Bootstrap", "自举采样"),
    "sar8j_r1_cdac": ("CDAC", "CDAC"),
    "sar_strongarm_t28": ("StrongARM", "StrongARM"),
    "sar8_se_ctrl": ("SAR controller", "SAR 控制器"),
    "sar8i_refword": ("Reference drive", "参考驱动"),
}
BLOCKS = {
    "bootstrap_n": (("Boot N", "自举 N"), "bootstrap", "bootstrap"),
    "bootstrap_p": (("Boot P", "自举 P"), "bootstrap", "bootstrap"),
    "cdac": (("MOM CDAC", "MOM CDAC"), "cdac", "cdac"),
    "comparator": (("StrongARM", "StrongARM"), "comparator", "comparator"),
    "reference": (("Reference drive", "参考驱动"), "reference", "reference"),
    "sar": (("SAR", "SAR"), "sar", "sar"),
}


def git_output(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def frozen_file(path):
    return git_output("show", f"{REVISION}:{path}")


def schematic_workspace(base_url, upgrader, checker):
    workspace = json.loads((ROOT / "design/rnl/workspace.json").read_text(encoding="utf-8"))
    design = json.loads((ROOT / "design/manifest.json").read_text(encoding="utf-8"))
    revision = git_output("rev-parse", "HEAD").decode().strip()
    workspace.update(
        base=f"{base_url}rnl/source/",
        level=design["top"],
        source={"repo": "chenzc24/sar-adc-t28", "commit": revision, "url": f"{REPOSITORY}/commit/{revision}"},
    )
    source_paths = set()
    for item in workspace["files"]:
        relative = PurePosixPath(item["path"])
        if relative.parts[0] != "design" or ".." in relative.parts or relative.suffix not in {".scs", ".rnl"}:
            raise SystemExit(f"Invalid schematic workspace path {relative}")
        content = (ROOT / relative).read_bytes()
        if len(content) != item["size"] or hashlib.sha256(content).hexdigest() != item["sha256"]:
            raise SystemExit(f"Regenerate the native RNL workspace after changing {relative}")
        source_paths.add(relative.as_posix())
    if RNL_ENTRY not in source_paths:
        raise SystemExit("Regenerate the portable RNL source for the current DUT.")
    drawing = json.loads((ROOT / "design/rnl/manifest.json").read_text(encoding="utf-8"))
    dut = ROOT / "design/dut.scs"
    if hashlib.sha256(dut.read_bytes()).hexdigest() != drawing["source_hashes"]["design/dut.scs"]:
        raise SystemExit("Regenerate the native RNL workspace for the current DUT entry.")
    levels = drawing["levels"]
    if any(level not in levels for level in SCHEMATIC_LEVELS):
        raise SystemExit("Check the site's schematic module links against the current hierarchy.")
    entry = convert(ROOT / RNL_ENTRY, upgrader, checker)
    workspace["entry"] = RNL_ENTRY
    workspace["files"] = [{"path": RNL_ENTRY, "size": len(entry), "sha256": hashlib.sha256(entry).hexdigest()}]
    files = {f"rnl/source/{RNL_ENTRY}": entry}
    files["rnl/workspace.json"] = json.dumps(workspace, indent=2).encode()

    return files, workspace


def schematic_context(workspace, base_url, locale):
    scheme, host, *_ = urlsplit(base_url)
    chinese = locale == "zh-CN"

    def url(level, embed=False):
        params = {"manifest": f"{base_url}rnl/workspace.json", "level": level}
        if embed:
            params.update(embed="1", origin=f"{scheme}://{host}")
        return html.escape(f"{RNL_VIEWER}?{urlencode(params)}", quote=True)

    links = "\n".join(f'<a href="{url(level, True)}" data-level="{level}" target="rnl-frame">{labels[chinese]}</a>'
                      for level, labels in SCHEMATIC_LEVELS.items())
    return {
        "rnl_embed": url(workspace["level"], True),
        "rnl_full": url(workspace["level"]),
        "rnl_links": links,
        "rnl_version": "0.4",
        "rnl_top": workspace["level"],
        "rnl_revision": workspace["source"]["commit"][:7],
        "rnl_entry": f'rnl/source/{workspace["entry"]}',
    }


def floorplan(locale):
    plan = json.loads(frozen_file("Layout/design/floorplan.json"))
    xmin, ymin, xmax, ymax = plan["core_bbox"]
    width, height = xmax - xmin, ymax - ymin
    regions = []
    for block in plan["blocks"]:
        labels, anchor, theme = BLOCKS[block["id"]]
        x, y = block["origin"]
        w, h = block["size"]
        position = (
            f"--x:{100 * (x - xmin) / width:.4f}%;--y:{100 * (ymax - y - h) / height:.4f}%;"
            f"--w:{100 * w / width:.4f}%;--h:{100 * h / height:.4f}%"
        )
        regions.append(
            f'<a class="region region-{theme}" style="{position}" '
            f'href="#{anchor}"><span>{labels[locale == "zh-CN"]}</span></a>'
        )
    return "\n".join(regions)


def navigation(current, locale):
    links = []
    for page, (label, _) in PAGES[locale].items():
        active = ' aria-current="page"' if page == current else ""
        links.append(f'<a href="{page}.html"{active}>{label}</a>')
    return "\n".join(links)


def render_pages(workspace, base_url):
    layout = Template((SITE / "layout.html").read_text(encoding="utf-8"))
    shared = {
        "repository": REPOSITORY,
        "snapshot": SNAPSHOT,
        "revision": REVISION,
        "short_revision": REVISION[:7],
    }
    pages = {}
    for locale, entries in PAGES.items():
        chinese = locale == "zh-CN"
        prefix = "zh/" if chinese else ""
        alternate_prefix = "../" if chinese else "zh/"
        context = {
            **shared,
            **schematic_context(workspace, base_url, locale),
            "locale": locale,
            "asset_base": "../" if chinese else "",
            "floorplan": floorplan(locale),
            "skip": "跳到正文" if chinese else "Skip to content",
            "nav_label": "主导航" if chinese else "Main navigation",
            "switch_locale": "en" if chinese else "zh-CN",
            "switch_label": "English" if chinese else "中文",
            "evidence_label": "数据快照" if chinese else "Evidence snapshot",
        }
        for name, (label, description) in entries.items():
            filename = f"{prefix}{name}.html"
            article = Template((SITE / "pages" / filename).read_text(encoding="utf-8"))
            pages[filename] = layout.substitute(
                context,
                language_link=f"{alternate_prefix}{name}.html",
                title=html.escape(f"{label} · SAR ADC T28"),
                description=html.escape(description),
                navigation=navigation(name, locale),
                content=article.substitute(context),
            )
        for legacy, (name, fragment) in REDIRECTS.items():
            target = f"{name}.html#{fragment}"
            label = entries[name][0]
            pages[f"{prefix}{legacy}.html"] = (
                f'<!doctype html><html lang="{locale}"><head><meta charset="utf-8">'
                f'<title>{label} · SAR ADC T28</title>'
                f'<noscript><meta http-equiv="refresh" content="0; url={target}"></noscript></head><body>'
                f'<a href="{target}" id="moved-page">{label}</a>'
                f'<script src="{context["asset_base"]}assets/language.js" defer></script></body></html>'
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
                path = posixpath.normpath(posixpath.join(posixpath.dirname(name), unquote(target.path))) if target.path else name
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


def build(output, base_url, upgrader, checker):
    base_url = base_url.rstrip("/") + "/"
    schematic, workspace = schematic_workspace(base_url, upgrader, checker)
    artifacts = {**schematic, **layout_artifacts()}
    pages = render_pages(workspace, base_url)
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
    parser.add_argument("--rnl-upgrader", default="rnl-upgrade-0.5.7")
    parser.add_argument("--rnl-checker", default="rnl")
    args = parser.parse_args()
    build(args.output.resolve(), args.base_url, args.rnl_upgrader, args.rnl_checker)
