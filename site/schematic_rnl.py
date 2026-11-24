"""Publish the current Spectre drawing as an RNL 0.4 netlist."""

from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory


RECORD = re.compile(r"(?ms)^// BEGIN SARADC RNL\n(.*?)^// END SARADC RNL$")
COORDINATE = r"\(-?\d+(?:\.\d+)?,-?\d+(?:\.\d+)?\)"
POINT = re.compile(COORDINATE)
DOT = re.compile(rf"// \$JUNCTION @ATTACH ({COORDINATE});")
WIRE = re.compile(r"// (.+?) @WIRE\(.*?\) \{(.*?)\};")
SYMBOL_PACKAGE = '// @USE-PACKAGE(name="sar8",version="0.1") {\n'
MOS_SYMBOLS = """// $SAR_NMOS_4TERM = @DEFINE-SYMBOL(box=[-3,-2,1,2]) {
//   $NMOS;
//   %b = (1,0) @PIN(terminal="b",direction="right");
//   @LINE {(-1.37,0) %b};
// };
// $SAR_PMOS_4TERM = @DEFINE-SYMBOL(box=[-3,-2,1,2]) {
//   $PMOS;
//   %b = (1,0) @PIN(terminal="b",direction="right");
//   @LINE {(-1.37,0) %b};
// };
"""


def name_junctions(record):
    """Use a shared point on each wire on the net at an authored junction."""
    lines = record.group(1).splitlines()
    nets = defaultdict(Counter)
    for line in lines:
        wire = WIRE.fullmatch(line)
        if wire:
            for point in set(POINT.findall(wire[2])):
                nets[point][wire[1]] += 1

    junctions = {}
    for line in lines:
        dot = DOT.fullmatch(line)
        if not dot or dot[1] in junctions:
            continue
        branches = [net for net, count in nets[dot[1]].items() if count > 1]
        if len(branches) > 1 or (not branches and len(nets[dot[1]]) > 1):
            raise ValueError(f"Ambiguous authored junction at {dot[1]}")
        net = branches[0] if branches else next(iter(nets[dot[1]]), None)
        if net is None:
            raise ValueError(f"Authored junction without a wire at {dot[1]}")
        junctions[dot[1]] = (f"%sar_j{len(junctions) + 1}", net)

    if not junctions:
        return record[0]
    output = ["// BEGIN SARADC RNL", lines[0]]
    output.extend(f"// {name} = {point};" for point, (name, _) in junctions.items())
    for line in lines[1:]:
        dot = DOT.fullmatch(line)
        wire = WIRE.fullmatch(line)
        if dot:
            line = f"// $JUNCTION @ATTACH {junctions[dot[1]][0]} => @PLACE{dot[1]};"
        elif wire:
            def wire_point(match):
                point = match[0]
                name, net = junctions.get(point, (point, None))
                return name if net == wire[1] else point

            line = line[:wire.start(2)] + POINT.sub(wire_point, wire[2]) + line[wire.end(2):]
        output.append(line)
    return "\n".join([*output, "// END SARADC RNL"])


def spectre_statements(source):
    return [line for line in source.splitlines() if line.strip() and not line.lstrip().startswith("//")]


def convert(source, upgrader, checker):
    original = source.read_text(encoding="utf-8")
    with TemporaryDirectory(prefix="saradc-rnl-") as scratch:
        directory = Path(scratch)
        entry = directory / source.name
        if '@VERSION("0.3")' in original:
            report = directory / "upgrade.json"
            result = subprocess.run([upgrader, "upgrade", source, "-o", directory, "--report", report],
                                    capture_output=True, encoding="utf-8")
            if not entry.is_file() or not report.is_file():
                raise ValueError(result.stderr or result.stdout)
            review = json.loads(report.read_text(encoding="utf-8"))
            if (review["discarded_placements"] or review["rule_changes"]
                or any(file["unconverted"] or file["needs_solve"] for file in review["files"])
                or any(item["severity"] == "error" for item in review["diagnostics"])):
                raise ValueError("RNL upgrade could not preserve the drawing")
            upgraded = entry.read_text(encoding="utf-8")
            # The standard 0.4 four-terminal MOS moves the bulk pin from (1,0) to (0,0).
            # Preserve the authored wire endpoints with an explicit visible bulk pin.
            upgraded = re.sub(r"\$(N|P)MOS_4TERM\b", r"$SAR_\1MOS_4TERM", upgraded)
            if SYMBOL_PACKAGE not in upgraded:
                raise ValueError("Missing SAR ADC symbol package in the current netlist")
            upgraded = upgraded.replace(SYMBOL_PACKAGE, SYMBOL_PACKAGE + MOS_SYMBOLS, 1)
            upgraded = RECORD.sub(name_junctions, upgraded)
        else:
            upgraded = original
        if '@VERSION("0.4")' not in upgraded or spectre_statements(original) != spectre_statements(upgraded):
            raise ValueError("Expected an RNL 0.4 drawing with the original Spectre statements")
        entry.write_text(upgraded, encoding="utf-8", newline="\n")
        result = subprocess.run([checker, "check", entry], capture_output=True, encoding="utf-8")
        if result.returncode:
            errors = [line for line in result.stdout.splitlines() if line.startswith("error ")]
            raise ValueError(result.stderr or "\n".join(errors[:20]) or result.stdout[-1000:])
        print(f"RNL 0.4 check: {result.stdout.splitlines()[-1]}")
        return entry.read_bytes()
