"""Run the private T28 MOM pilot on the licensed host; raw evidence stays there."""

from __future__ import print_function

import argparse
import hashlib
import json
import os
from os.path import basename, dirname, isfile, join
import re
import struct
import subprocess
import socket
import tarfile
if __package__:
    from . import workspace
else:
    import workspace

try:
    from shlex import quote
except ImportError:
    from pipes import quote

PDK = "/home/process/tsmc28n/PDK_mmWave/iPDK_CRN28HPC+ULL_v1.8_2p2a_20190531/tsmcN28"
RULES = "/home/dmanager/shared_lib/TSMC28/calibre_rule"
PEX_RUNSET = "/home/dmanager/shared_lib/TSMC28/calibre/runset_pex"
CADENCE = "/home/cshrc/.cshrc.cadence.IC618SP201"
CALIBRE = "/home/cshrc/.cshrc.mentor"
LIB = "SAR_ADC_T28_LAYOUT"
LIB_PATH = "/home/chenzc_intern25/TSMC28/llm_IO/SAR_ADC_T28_LAYOUT"
CASES = {
    "unit": ("sar8_mom_unit", 0.5, False),
    "baseline": ("sar8_mom_ratio", 0.5, False),
    "open": ("sar8_mom_ratio", 0.5, True),
    "reroute": ("sar8_mom_ratio", 3.5, False),
    "rollback": ("sar8_mom_ratio", 0.5, False),
    "compact": ("sar8_mom_ratio", None, False),
    "full": ("sar8j_r1_cdac", None, False),
    "comparator": ("sar_strongarm_t28_core", None, False),
    "comparator-filled": ("sar_strongarm_t28", None, False),
    "bootstrap": ("sar_bootstrap_flat_8b_p_core", None, False),
}
COMPARATOR_PORTS = sorted(("CLK", "OUTN", "OUTP", "VDD", "VINN", "VINP", "VSS"))
BOOTSTRAP_PORTS = sorted(("CLKS", "VOUT", "VIN", "VDD", "VSS"))
BOOTSTRAP_FILL_RULES = {"OD.S.14", "OD.DN.3", "PO.DN.3", "PO.DN.3.1"}
COMPACT_PORTS = sorted(("TOP", "B0", "B1", "GN0", "GP0", "GN1", "GP1", "VDD", "VSS", "VREFN", "VREFP"))
FULL_PORTS = sorted(["G"+s+p+str(b) for s in "NP" for p in "NP" for b in range(8)] +
                    ["TOPN", "TOPP", "VDD", "VSS", "VREFN", "VREFP"])
FIXTURE_DRC_MARKERS = {
    "IO_CONNECT_CORE_NET_VOLTAGE_IS_CORE:WARNING1",
    "DIODMY_L:WARNING",
    "PO.DN.3.1",
}
FULL_CONTEXT_RULES = {
    "OD.S.14", "OD.DN.3", "PO.DN.3", "PO.DN.3.1",
    "M2.DN.1", "M4.DN.1", "M5.DN.1", "M6.DN.1", "M7.DN.1", "M7.DN.6",
    "Mx.DN.7:M1_M2_M3", "Mx.DN.7:M5_M6_M7",
}


def drc_blockers(rules, case):
    # These results remain DRC failures. Permit pre-fill electrical diagnosis
    # only once the actual spacing/width/connectivity issues have been fixed.
    deferred = FULL_CONTEXT_RULES if case == "full" else set()
    if case == "comparator":
        deferred = {"OD.DN.3", "PO.DN.3", "PO.DN.3.1"}
    if case == "bootstrap":
        deferred = BOOTSTRAP_FILL_RULES
    return set(rules) - FIXTURE_DRC_MARKERS - deferred


def sha(data):
    return hashlib.sha256(data).hexdigest()


def raw(path):
    with open(path, "rb") as stream:
        return stream.read()


def put(path, data):
    with open(path, "wb") as stream:
        stream.write(data)


def gds_identity(path, omit_references=()):
    """Hash the stream and its geometry independent of XStream's PCell names."""
    gds = raw(path)
    stable = hashlib.sha256()
    names = {}
    elements = {}
    structure = None
    element = []
    offset = 0
    while offset < len(gds):
        size, record = struct.unpack_from(">HB", gds, offset)
        if size < 4 or size % 2 or offset + size > len(gds):
            raise ValueError("Bad GDS record at {}".format(offset))
        payload = gds[offset + 4 : offset + size]
        if record == 0x06:
            structure = payload.rstrip(b"\0").decode("ascii")
            names.setdefault(structure, [])
            elements[structure] = []
        elif record == 0x07:
            if element:
                raise ValueError("Unterminated GDS element")
            structure = None
        elif structure:
            if record == 0x19:
                names[structure].append(payload.rstrip(b"\0").decode("ascii"))
            element.append((record, payload, gds[offset : offset + size]))
            if record == 0x11:
                elements[structure].append(element)
                element = []
        stable.update(gds[offset : offset + (4 if record in (0x01, 0x05) else size)])
        offset += size
        if record == 0x04:  # ENDLIB; XStream pads the end of the last GDS block.
            if gds[offset:].strip(b"\0"):
                raise ValueError("Unexpected data after GDS ENDLIB")
            break
    else:
        raise ValueError("Missing GDS ENDLIB")
    canonical = {}

    def geometry(name):
        if name not in canonical:
            canonical[name] = sha(b"".join(sorted(
                hashlib.sha256(b"".join(
                    ("SREF:" + geometry(payload.rstrip(b"\0").decode("ascii"))).encode("ascii")
                    if record == 0x12 else blob
                    for record, payload, blob in group
                )).digest()
                for group in elements[name]
                if not any(record == 0x12 and payload.rstrip(b"\0").decode("ascii") in omit_references
                           for record, payload, blob in group)
            )))
        return canonical[name]

    return {"sha256": sha(gds), "without_gds_timestamps": stable.hexdigest(),
            "structural_sha256": {name: geometry(name) for name in names}, "labels": names}


def replace_once(text, pattern, line):
    updated, n = re.subn(pattern, lambda _: line, text, flags=re.MULTILINE)
    if n != 1:
        raise ValueError("Expected one deck statement: " + pattern)
    return updated


def prepare_deck(out, name, top, distributed_supplies=()):
    path = {
        "drc": join(RULES, "drc/drc_rule_T28_cell"),
        "lvs": join(RULES, "lvs/calibre.lvs"),
        "pex": join(RULES, "rcx/calibre.rcx"),
    }[name]
    data = raw(path)
    text = data.decode("latin1")
    for directive, value in (
        ("LAYOUT PATH", "fixture.gds"),
        ("LAYOUT PRIMARY", top),
    ):
        text = replace_once(text, r'^' + directive + r'[ \t]+"[^"]*"[^\n]*', '{} "{}"'.format(directive, value))
    support = {}
    if name == "drc":
        text = replace_once(text, r'^DRC RESULTS DATABASE[^\n]*', 'DRC RESULTS DATABASE "DRC_RES.db" ASCII')
    else:
        text = replace_once(text, r'^SOURCE PRIMARY[^\n]*', 'SOURCE PRIMARY "{}"'.format(top))
        text = replace_once(
            text, r'^SOURCE PATH[^\n]*',
            'SOURCE PATH "{}" "../reference.cdl"'.format(join(dirname(path), "source.added")),
        )
        # Preserve the installed deck's DFM and all rule switches. Resolve its
        # relative includes against the installed deck, not the job directory.
        text = re.sub(
            r'(?im)^(\s*include[ \t]+)\./([^ \t\r\n]+)',
            lambda m: m.group(1) + join(dirname(path), m.group(2)), text,
        )
        if name == "pex":
            if distributed_supplies:
                # Enable only the requested rails in this job's deck copy.
                def include_rails(match):
                    tokens = re.findall(r'"[^"]+"', match.group(1))
                    if not tokens or " ".join(tokens) != " ".join(match.group(1).split()):
                        raise ValueError("Unsupported PEX EXTRACT EXCLUDE syntax")
                    other = [token for token in tokens if token[1:-1] not in distributed_supplies]
                    return "PEX EXTRACT EXCLUDE " + " ".join(other) if other else ""

                text = re.sub(r'(?im)^[ \t]*PEX[ \t]+EXTRACT[ \t]+EXCLUDE[ \t]+([^\r\n]+)', include_rails, text)
                support["distributed_supplies"] = list(distributed_supplies)
            # The installed xRC deck recommends flattening inserted dummy
            # patterns. Expand only our fixed fill masters and their children;
            # preserve functional hierarchy and all fill geometry.
            # ACF*/sar8_adc_core_fill*: the ADC core fill hierarchy (Layout/design/toplevel_fill.py), not its wrapper.
            fill_cells = sorted(cell for cell in gds_identity(join(out, "fixture.gds"))["labels"]
                                if cell.startswith(("CDFO_", "CDFM_", "sar8_cdac_fill_", "SCFO_", "SCFM_", "sar8_comp_fill_",
                                                    "STFO_", "STFM_", "sar8_timing_fill_", "ACF", "sar8_adc_core_fill"))
                                and not cell.startswith("sar8_adc_core_filled"))
            if fill_cells:
                text = replace_once(text, r'^//FLATTEN CELL TOP_CELL_DM TOP_CELL_DODDPO[^\n]*',
                                    "FLATTEN CELL " + " ".join(fill_cells))
                support["dummy_flatten_cells"] = fill_cells
            text = replace_once(
                text, r'^PEX NETLIST[ \t]+"net\.dist"[^\n]*',
                'PEX NETLIST "extracted.scs" SPECTRE LAYOUTNAMES LOCATION RCNAMED',
            )
            mapping = join(dirname(path), "BA_mapping")
            support["BA_mapping"] = {"path": mapping, "sha256": sha(raw(mapping))}
            os.symlink(mapping, join(out, "BA_mapping"))
            # The lab GUI runset adds MOM-device capacitance exclusions that
            # are absent in the standalone base deck. Import just that approved
            # directive list; the compact model still accounts for MOM itself.
            runset = raw(PEX_RUNSET)
            line = re.search(r"(?m)^\*pexSVRFCmds:[ \t]*(.*)$", runset.decode("latin1"))
            if not line:
                raise ValueError("Missing lab runset MOM capacitance exclusions")
            commands = re.findall(r"\{(PEX IGNORE CAPACITANCE DEVICE M\d M\d MOMDMY\d)\}", line.group(1))
            expected = ["PEX IGNORE CAPACITANCE DEVICE M{0} M{0} MOMDMY{0}".format(i)
                        for i in range(1, 8)]
            if commands != expected:
                raise ValueError("Lab runset MOM exclusion scope changed")
            # Keep these in the deck's SVRF block; its tail switches to TVF.
            format_statement = 'PEX NETLIST "extracted.scs" SPECTRE LAYOUTNAMES LOCATION RCNAMED'
            text = replace_once(text, r'^' + re.escape(format_statement) + r'[ \t]*$',
                                format_statement + "\n" + "\n".join(commands))
            support["mom_runset"] = {"path": PEX_RUNSET, "sha256": sha(runset),
                                     "mom_device_exclusions": len(commands)}
    put(join(out, name + ".svrf"), text.encode("latin1"))
    return {"path": str(path), "sha256": sha(data), "job_sha256": sha(text.encode("latin1")), "support": support}


def drc_rules(path):
    data = read(path)
    return {rule: int(n) for rule, n in re.findall(r"(?m)^([A-Za-z0-9_.:-]+)\r?\n(\d+) \d+ \d+ ", data)
            if int(n)}


def read(path):
    return raw(path).decode("utf-8", "replace") if isfile(path) else ""


def same_source_text(prior, expected, current):
    """Allow only platform line-ending changes, preserving frozen identities."""
    if set(expected) != set(current):
        return False
    for name, digest in expected.items():
        if basename(name) != name:
            return False
        old = raw(join(prior, name))
        if sha(old) != digest:
            raise ValueError('Frozen source identity changed: ' + name)
        if old.replace(b'\r\n', b'\n') != current[name].replace(b'\r\n', b'\n'):
            return False
    return True


def tool(setup, args, cwd, log, seconds):
    command = "source {}; exec {}".format(setup, " ".join(quote(str(x)) for x in args))
    fd = os.open(log, os.O_CREAT | os.O_WRONLY | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream, open(os.devnull, "rb") as no_input:
        return subprocess.call(
            ["timeout", "-k", "10", str(seconds), "tcsh", "-fc", command],
            cwd=cwd, stdin=no_input, stdout=stream, stderr=subprocess.STDOUT,
        )


def run(root, out, case, through, source_stream=None, extract_only=False, existing_oa=False, pex_timeout=300, omit_fill=None, view='layout'):
    top, extension, open_b1 = CASES[case]
    # A Bootstrap sampler candidate lives in its own view, layout_mmain<N>; a revision of the selected sampler
    # (same electrical source and LVS reference) in layout_r<N>.
    candidate = re.match(r"\Alayout_(mmain([1-9][0-9]?))\Z", view) if case == 'bootstrap' else None
    revision = re.match(r"\Alayout_r([2-9]|[1-9][0-9])\Z", view) if case == 'bootstrap' else None
    if view != 'layout' and not (view == 'layout_paired_balanced' and case == 'full' and existing_oa and not source_stream) \
            and not ((candidate or revision) and not source_stream):
        raise ValueError('Alternate view requires an existing CDAC layout or a Bootstrap candidate or revision view')
    log = {"case": case, "top": top, "library": LIB, "library_path": LIB_PATH, "b1_extension_um": extension,
           "open_b1": open_b1, "checks": {}, "decks": {}}
    log['execution_host']=socket.gethostname()
    log['oa_view']=view
    log['workspace_configuration_sha256']=sha(raw(join(root,'workspace.json')))
    log['driver_sha256']={name:sha(raw(join(root,name))) for name in ('run_physical.py','workspace.py')}
    if omit_fill and (case != 'full' or not source_stream or extract_only or existing_oa):
        raise ValueError('Fill ablation requires a full source stream and fresh physical checks')
    if omit_fill:
        log['driver_sha256'].update({name: sha(raw(join(root, name)))
                                    for name in ('fill_ablation.py',)})

    def save():
        tmp = join(out, "manifest.next")
        put(tmp, (json.dumps(log, indent=2, sort_keys=True) + "\n").encode("ascii"))
        os.rename(tmp, join(out, "manifest.json"))

    def launch(phase, setup, args, directory, seconds):
        log["checks"][phase] = {"status": "running", "args": [str(x) for x in args]}
        save()
        rc = tool(setup, args, directory, join(out, phase + ".console"), seconds)
        log["checks"][phase].update(status="exited", returncode=rc)
        save()
        if rc:
            raise RuntimeError("{} exited {}; see {}".format(phase, rc, out))

    try:
        # Preserve the actual driver/config bytes, not only a mutable deployment.
        for name in list(log['driver_sha256']) + ['workspace.json', 'cds.lib']:
            put(join(out, name), raw(join(root, name)))
        generator = {"compact": "compact.il", "full": "cdac-full.il", "comparator": "comparator.il", "comparator-filled": "comparator-wrapper.il", "bootstrap": "bootstrap.il"}.get(case, "mom.il")
        if view == 'layout_paired_balanced':
            generator = 'cdac-paired.il'
        reference = join(root, {"compact": "compact-reference.cdl", "full": "cdac-full-reference.cdl", "comparator": "comparator-reference.cdl", "comparator-filled": "comparator-filled-reference.cdl", "bootstrap": "bootstrap-reference.cdl"}.get(case, "reference.cdl"))
        if candidate:
            reference = join(root, "bootstrap-" + candidate.group(1) + "-reference.cdl")
            log["sampler_candidate"] = candidate.group(1)
        log["source_sha256"] = {basename(p): sha(raw(p)) for p in (join(root, generator), reference)}
        for path in (join(root, generator), reference):
            put(join(out, basename(path)), raw(path))
        if existing_oa:
            log['oa_mode'] = 'read_existing_owned_cell'
            if case in ('full','comparator-filled'):
                applied=workspace.state('fill_applied.json' if case=='full' else 'comparator-fill-applied.json')
                if isfile(applied):
                    log['fill_application']=json.loads(read(applied))
        checkpoint = None
        if case in ("open", "reroute", "rollback"):
            checkpoint = json.loads(read(workspace.state("checkpoint.json")))
            if checkpoint["source_sha256"] != log["source_sha256"]:
                raise ValueError("Current generator and reference differ from the rolling checkpoint")
            if checkpoint["b1_extension_um"] != CASES["baseline"][1] or checkpoint["open_b1"]:
                raise ValueError("Invalid baseline checkpoint")
            log["rollback_source"] = checkpoint
        put(join(out, "reference.cdl"), raw(reference))
        gds_path = join(out, "fixture.gds")
        if source_stream:
            prior = workspace.evidence(source_stream)
            old = json.loads(read(join(prior, "manifest.json")))
            equivalent_sources = same_source_text(prior, old['source_sha256'],
                                                  {basename(p): raw(p) for p in (join(root,generator),reference)})
            log['source_stream_inputs_equal_except_line_endings'] = equivalent_sources
            if (old["case"] != case or not equivalent_sources or
                    any(old["checks"].get(key, {}).get("returncode") != 0 for key in ("oa", "stream"))):
                raise ValueError("Existing stream is not from the same successful OA and inputs")
            if "PILOT_OA_OK " + top not in read(join(prior, "oa.console")):
                raise RuntimeError("No saved OA readback in existing evidence")
            source_gds = join(prior, "fixture.gds")
            if old.get('gds', {}).get('sha256') != sha(raw(source_gds)):
                raise ValueError('Source stream identity changed')
            if omit_fill:
                from fill_ablation import derive
                log['diagnostic'] = derive(source_gds, gds_path, top, omit_fill)
            else:
                put(gds_path, raw(source_gds))
            log["stream_evidence"] = source_stream
            if extract_only:
                if (old.get("gds", {}).get("sha256") != sha(raw(gds_path)) or
                        old["checks"].get("lvs", {}).get("verdict") != "CORRECT" or
                        "markers" not in old["checks"].get("drc", {})):
                    raise ValueError("Cannot reuse missing DRC or LVS evidence")
                log["checks"].update({key: dict(old["checks"][key], source=source_stream)
                                      for key in ("drc", "lvs")})
                log["checks"]["drc"]["markers_by_rule"] = drc_rules(join(prior, "drc", "DRC_RES.db"))
                rules = log["checks"]["drc"]["markers_by_rule"]
                if sum(rules.values()) != old["checks"]["drc"]["markers"] or drc_blockers(rules, case):
                    raise RuntimeError("Source has unclassified DRC markers")
                if case == "full":
                    log["checks"]["drc"]["verdict"] = "NOT_CLEAN" if rules else "CLEAN"
                    log["checks"]["drc"]["deferred_context_rules"] = sorted(set(rules) & FULL_CONTEXT_RULES)
                    log["physical_signoff"] = False
        else:
            entry = join(out, "build.il")
            if existing_oa:
                count = 7 if case.startswith("comparator") else 38
                if case == "bootstrap":
                    count = len(BOOTSTRAP_PORTS)
                build = '''let((cv)
cv=dbOpenCellViewByType("SAR_ADC_T28_LAYOUT" "%s" "%s" "" "r")
unless(cv && length(cv~>terminals)==%d error("Invalid existing layout\\n"))
printf("PILOT_OA_OK %s instances=%%d ports=%%d bbox=%%L\\n" length(cv~>instances) length(cv~>terminals) cv~>bBox)
dbClose(cv))
exit(0)
''' % (top, view, count, top)
            elif case in ("compact", "full", "comparator", "bootstrap"):
                if case in ("comparator", "bootstrap"):
                    cell_path = join(LIB_PATH, top)
                    if os.path.isdir(cell_path):
                        if any(name.endswith(('.cdslck', '.cdslck.RHEL')) or '.cdslck' in name
                               for directory, dirs, files in os.walk(cell_path) for name in files):
                            raise RuntimeError(top + " OA is locked by another editor")
                        backup = join(out, 'before-' + case + '-oa.tar.gz')
                        with tarfile.open(backup, 'w:gz') as archive:
                            archive.add(cell_path, arcname=top)
                        log['oa_checkpoint_sha256'] = sha(raw(backup))
                        if candidate or revision:
                            # Building another view must leave every existing view of the cell unchanged.
                            log['other_views_layout_oa_sha256'] = dict(
                                (v, sha(raw(join(cell_path, v, 'layout.oa')))) for v in sorted(os.listdir(cell_path))
                                if v != view and isfile(join(cell_path, v, 'layout.oa')))
                build = 'load("{}")\n'.format(join(out, generator))
                if candidate:
                    build = 'bsView = "{}"\nbsMainFingers = {}\n'.format(view, int(candidate.group(2))) + build
                elif revision:
                    build = 'bsView = "{}"\n'.format(view) + build
            else:
                build = 'pilotCell = "{}"\npilotB1Extension = {}\npilotOpenB1 = {}\nload("mom.il")\n'.format(
                    top, extension, "t" if open_b1 else "nil"
                )
            put(entry, build.encode("ascii"))
            launch("oa", CADENCE, ["virtuoso", "-nograph", "-nocdsinit", "-log",
                                  join(out, "oa.ciw.log"), "-restore", entry], root, 300 if case == "full" else 100)
            if "PILOT_OA_OK " + top not in read(join(out, "oa.console")):
                raise RuntimeError("No saved OA readback")
            for v, digest in log.get('other_views_layout_oa_sha256', {}).items():
                if sha(raw(join(LIB_PATH, top, v, 'layout.oa'))) != digest:
                    raise RuntimeError('The build changed the existing view ' + v)
            launch("stream", CADENCE, ["strmout", "-library", LIB, "-strmFile", gds_path,
                                       "-topCell", top, "-view", view, "-layerMap", join(PDK, "tsmcN28.layermap"),
                                       "-logFile", join(out, "stream.log"), "-summaryFile", join(out, "stream.sum"),
                                       "-cdslib", join(root, "cds.lib"), "-runDir", out, "-convertPin", "geometry",
                                       "-convertPcellPin", "geometry"], root, 100)
        gds = gds_identity(gds_path)
        log["gds"] = gds
        ports = ["B0", "TOP"] if case == "unit" else ["B0", "B1", "TOP"]
        if case == "compact":
            ports = COMPACT_PORTS
        if case == "full":
            ports = FULL_PORTS
        if case.startswith("comparator"):
            ports = COMPARATOR_PORTS
        if case == "bootstrap":
            ports = BOOTSTRAP_PORTS
        if sorted(gds["labels"].get(top, [])) != ports:
            raise RuntimeError("Top GDS labels differ from fixture ports")
        if case == "rollback" and gds["structural_sha256"][top] != checkpoint["geometry_sha256"]:
            raise RuntimeError("Rollback did not restore the checkpoint geometry")
        unexpected_drc = False
        for name in ("drc", "lvs", "pex"):
            if through == "stream" or (open_b1 and name == "pex"):
                break
            if extract_only and name != "pex":
                continue
            work = join(out, name)
            os.mkdir(work)
            os.symlink("../fixture.gds", join(work, "fixture.gds"))
            log["decks"][name] = prepare_deck(work, name, top)
            if name == "drc":
                launch(name, CALIBRE, ["calibre", "-drc", "-hier", "-turbo", "4", "-nowait", "drc.svrf"], work, 300)
                report = read(join(work, "DRC.rep"))
                count = re.search(r"TOTAL DRC Results Generated:\s*(\d+)", report, re.I)
                if not count:
                    raise RuntimeError("Missing DRC summary count")
                log["checks"][name]["markers"] = int(count.group(1))
                log["checks"][name]["markers_by_rule"] = drc_rules(join(work, "DRC_RES.db"))
                rules = log["checks"][name]["markers_by_rule"]
                unexpected_drc = bool(sum(rules.values()) != int(count.group(1)) or drc_blockers(rules, case))
                if case == "full":
                    log["checks"][name]["verdict"] = "NOT_CLEAN" if rules else "CLEAN"
                    log["checks"][name]["deferred_context_rules"] = sorted(set(rules) & FULL_CONTEXT_RULES)
                    log["physical_signoff"] = False
                if case.startswith("comparator"):
                    log["checks"][name]["verdict"] = "NOT_CLEAN" if rules else "CLEAN"
                    log["checks"][name]["deferred_context_rules"] = sorted(set(rules) & {"OD.DN.3", "PO.DN.3", "PO.DN.3.1"})
                    log["physical_signoff"] = False
                if case == "bootstrap":
                    log["checks"][name]["verdict"] = "NOT_CLEAN" if rules else "CLEAN"
                    log["checks"][name]["deferred_fill_rules"] = sorted(set(rules) & BOOTSTRAP_FILL_RULES)
                    log["physical_signoff"] = False
                if unexpected_drc and case not in ("compact", "full", "comparator", "comparator-filled"):
                    raise RuntimeError("Unexpected DRC markers; inspect the original rule results")
            elif name == "lvs":
                # A comparison mismatch is a successful tool execution but
                # not a passing positive run. Require the reported verdict.
                launch(name, CALIBRE, ["calibre", "-lvs", "-hier", "-turbo", "4", "-nowait", "lvs.svrf"], work, 300)
                report = read(join(work, "lvs.rep"))
                match = re.search(
                    r"(?m)^[ \t]+(CORRECT|INCORRECT)[ \t]+" + re.escape(top) +
                    r"[ \t]+" + re.escape(top) + r"[ \t]*$", report)
                if not match:
                    raise RuntimeError("Missing LVS comparison verdict")
                verdict = match.group(1)
                log["checks"][name]["verdict"] = verdict
                if verdict != ("INCORRECT" if open_b1 else "CORRECT"):
                    raise RuntimeError("LVS verdict differs from the expected {}".format(case))
            else:
                launch("phdb", CALIBRE, ["calibre", "-xrc", "-phdb", "-turbo", "4", "-nowait", "pex.svrf"], work, 300)
                log['pex_rcc_wall_limit_seconds']=pex_timeout
                launch("rcc", CALIBRE, ["calibre", "-xrc", "-pdb", "-rcc", "-turbo", "4", "-nowait", "pex.svrf"], work, pex_timeout)
                launch("format", CALIBRE, ["calibre", "-xrc", "-fmt", "-all", "-nowait", "pex.svrf"], work, 300)
                extracted = join(work, "extracted.scs")
                if not isfile(extracted) or not os.stat(extracted).st_size:
                    raise RuntimeError("PEX did not generate the requested Spectre netlist")
                companion = {n: sha(raw(join(work, n))) for n in sorted(os.listdir(work))
                             if n.startswith("extracted.scs.")}
                log["checks"]["pex"] = {"sha256": sha(raw(extracted)), "bytes": os.stat(extracted).st_size,
                                        "companion_sha256": companion}
            if sha(raw(gds_path)) != gds["sha256"]:
                raise RuntimeError("GDS changed during verification")
            save()
            if through == name:
                break
        if unexpected_drc:
            raise RuntimeError("Unexpected DRC markers; inspect the original rule results")
    except Exception as exc:
        log["error"] = str(exc)
        raise
    finally:
        save()
    return log


def write_checkpoint(root, evidence_id, log):
    top = log["top"]
    gds = log["gds"]
    checkpoint = {
        "case": "baseline", "b1_extension_um": CASES["baseline"][1], "open_b1": False,
        "verified_stream": evidence_id, "source_sha256": log["source_sha256"],
        "gds_sha256": gds["sha256"], "geometry_sha256": gds["structural_sha256"][top],
    }
    temp = workspace.state("checkpoint.next")
    put(temp, (json.dumps(checkpoint, indent=2, sort_keys=True) + "\n").encode("ascii"))
    os.rename(temp, workspace.state("checkpoint.json"))


def main():
    import fcntl
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", choices=CASES)
    parser.add_argument("evidence_id")
    parser.add_argument("--through", choices=("stream", "drc", "lvs", "pex"))
    parser.add_argument("--source-stream", help="Reuse an already completed OA and stream-out evidence ID")
    parser.add_argument("--extract-only", action="store_true", help="Reuse source-stream DRC/LVS and extract its GDS")
    parser.add_argument("--omit-fill", choices=('metal', 'odpo'),
                        help="Diagnostic stream only: omit one top-level fill instance; rerun DRC/LVS/PEX")
    parser.add_argument("--pex-timeout",type=int,choices=(300,1800),default=300,help="RCC wall limit; filled macros may need 1800s")
    parser.add_argument("--existing-oa", action="store_true", help="Verify the current owned full CDAC without rebuilding it")
    parser.add_argument('--view', default='layout',
                        help='layout, layout_paired_balanced (existing CDAC), layout_mmain<N> (Bootstrap candidate) '
                             'or layout_r<N> (Bootstrap revision)')
    parser.add_argument("--rebuild-comparator", action="store_true", help="Explicitly rebuild the generator-owned comparator core")
    parser.add_argument("--rebuild-bootstrap", action="store_true", help="Explicitly rebuild the generator-owned Bootstrap core")
    parser.add_argument("--checkpoint", action="store_true", help="Save this verified working baseline as the rollback point")
    args = parser.parse_args()
    for core in ('comparator','bootstrap'):
        rebuild = getattr(args, 'rebuild_' + core)
        if rebuild and (args.case != core or args.existing_oa or args.source_stream):
            parser.error(core + ' rebuild needs its own core and a fresh physical run')
        if args.case == core and not (args.existing_oa or args.source_stream or rebuild):
            parser.error('Use --existing-oa or explicitly request --rebuild-' + core)
    if args.through is None:
        args.through = "lvs" if args.case in ("compact", "full") else "pex"
    if args.case == "compact" and args.through == "pex":
        parser.error("The switch routing fixture is qualified through LVS")
    if args.existing_oa and (args.case not in ('full', 'comparator', 'comparator-filled', 'bootstrap') or args.source_stream or args.checkpoint):
        parser.error("Existing-OA mode requires a supported current module")
    if not all(re.match(r"\A[a-z0-9][a-z0-9-]{1,55}\Z", name)
               for name in (args.evidence_id, args.source_stream) if name is not None):
        parser.error("Choose a unique short evidence ID")
    if args.extract_only and (not args.source_stream or args.through != "pex" or args.case == "open"):
        parser.error("Extraction-only needs matching successful physical evidence")
    if args.omit_fill and (args.case != 'full' or not args.source_stream or args.extract_only or args.existing_oa or args.checkpoint):
        parser.error("Fill ablation requires a source full-CDAC stream and fresh physical checks")
    if args.checkpoint and (args.case != "baseline" or args.through != "pex" or args.source_stream):
        parser.error("Checkpoint requires generating and verifying the actual working baseline")
    configured=workspace.paths()
    root=configured['runtime']
    if args.case not in ('comparator','bootstrap') and not args.existing_oa and not args.source_stream and not configured.get('allow_regeneration',False):
        parser.error('OA is checkpoint-owned: use --existing-oa; reconcile manual edits before allowing regeneration')
    if configured['library']!=LIB or configured['library_path']!=LIB_PATH:
        parser.error('Configured library differs from the native generator target')
    os.umask(0o077)
    libfile = join(root, "cds.lib")
    if not isfile(libfile):
        put(libfile, "DEFINE tsmcN28 {}\nDEFINE {} {}\n".format(PDK, LIB, LIB_PATH).encode("ascii"))
    if "DEFINE {} {}".format(LIB, LIB_PATH) not in read(libfile).splitlines():
        parser.error("cds.lib must map the unified layout library to llm_IO")
    with open(configured['lock'], "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        out = workspace.evidence(args.evidence_id,create=True)
        log = run(root, out, args.case, args.through, args.source_stream, args.extract_only, args.existing_oa, args.pex_timeout, args.omit_fill, args.view)
        if args.checkpoint:
            write_checkpoint(root, args.evidence_id, log)


if __name__ == "__main__":
    main()
