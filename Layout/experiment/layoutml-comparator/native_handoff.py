"""Translate the reviewed Meso-LML into an isolated native OA comparator and CDL.

Run locally with the same LayoutML checkout as review.py. This entry produces
the handoff packet only. The licensed host runs the SKILL and Calibre decks.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

import review

TOP = "sar_strongarm_lml_exp"
LIB = "SAR_ADC_T28_LAYOUT"
METAL = {"met1": "M1", "met2": "M2", "met3": "M3"}


def um(nm):
    return f"{nm / 1000:.4f}"


def point(x, y):
    return f"list({um(x)} {um(y)})"


def box(r):
    return f"list({point(*r[:2])} {point(*r[2:])})"


def center(r):
    return ((r[0] + r[2]) // 2, (r[1] + r[3]) // 2)


def reference():
    text = review.NETLIST.read_text(encoding="utf-8")
    header = re.search(r"^subckt sar_strongarm_t28 ([^\n]+)$", text, re.M)
    rows = re.findall(r"^\s*(M\w+) \(([^)]+)\) (\w+) l=(\S+) w=(\S+) multi=(\d+) nf=(\d+)", text, re.M)
    if not header or len(rows) != 11:
        raise ValueError("Unexpected electrical interface")
    devices = {}
    lines = [f"* Frozen electrical source {hashlib.sha256(review.NETLIST.read_bytes()).hexdigest()}",
             f".SUBCKT {TOP} {header[1].strip()}"]
    for name, nodes, model, length, width, multi, fingers in rows:
        if (length, multi, fingers) != ("30n", "1", "1"):
            raise ValueError(name)
        devices[name] = (nodes.split(), model, {"1u": 1000, "500n": 500}[width])
        lines.append(f"{name} {nodes} {model} L={length} W={width}")
    return devices, "\n".join(lines + [".ENDS " + TOP, ""])


IL_HELPERS = '''procedure(lmlRect(cv lay r net)
  let((f) f=dbCreateRect(cv list(lay "drawing") r)
    unless(f error("rectangle %s %L" lay r))
    when(net f~>net=dbFindNetByName(cv net)) f))
procedure(lmlVia(cv tech name pt pars)
  let((v) v=dbCreateVia(cv techFindViaDefByName(tech name) pt "R0" pars)
    unless(v error("via %s %L" name pt)) v))
procedure(lmlTerm(cv inst terminal net)
  let((term) term=dbFindTermByName(inst~>master terminal)
    unless(term && dbCreateInstTerm(dbFindNetByName(cv net) inst term)
      error("terminal %s.%s" inst~>name terminal))))
procedure(lmlPort(cv name r pt dir)
  let((net term f)
    net=dbFindNetByName(cv name)
    term=dbCreateTerm(net name dir)
    f=lmlRect(cv "M2" r name)
    unless(term && dbCreatePin(net f name term) error("pin %s" name))
    unless(dbCreateLabel(cv list("M2" "pin") pt name "centerCenter" "R0" "roman" 0.07)
      error("label %s" name))))
'''


def build(mc, destination, predecessor=None):
    metrics, compiled, ast, _ = review.evaluate(mc)
    if metrics["shorts"] or metrics["opens"]:
        raise ValueError("Draft connectivity failed")
    electrical, cdl = reference()
    net_names = sorted(metrics["nets"])
    commands = [IL_HELPERS, "procedure(lmlBuild() let((cv tech mast inst)",
                f'cv=dbOpenCellViewByType("{LIB}" "{TOP}" "layout" "maskLayout" "w")',
                'unless(cv error("cannot open experiment cell"))',
                'tech=techGetTechFile(cv)',
                f'dbReplaceProp(cv "lmlSourceSha256" "string" "{metrics["lml_sha256"]}")']
    commands += [f'dbMakeNet(cv "{n}")' for n in net_names]
    inventory = []
    for pc in ast["pcells"]:
        entry = compiled["store"]["realizations"][pc["realization"]]
        def placed(rect):
            return mc.transform_local_box(rect, *pc["atNm"], pc["orient"])
        layers = entry["layers_dbu_nm"]
        pins = {p["port"]: (p["net"], placed(p["box"])) for p in entry["ports_local_nm"]}
        if not pc["devices"]:
            # Body contact spacing and cut count follow the reviewed tap bars.
            rect = placed(layers["tap"][0])
            cuts = [placed(r) for r in layers["mcon"]]
            xs = sorted(center(r)[0] for r in cuts)
            assert all((r[2]-r[0], r[3]-r[1]) == (40, 40) for r in cuts)
            assert len(set(center(r)[1] for r in cuts)) == 1
            cut_spacing = xs[1]-xs[0]-40 if len(xs)>1 else 90
            assert all(b-a==cut_spacing+40 for a,b in zip(xs,xs[1:]))
            enc = point((rect[2]-rect[0]- (xs[-1]-xs[0]+40))//2, (rect[3]-rect[1]-40)//2)
            vt = "M1_NW" if pins["B"][0] == "VDD" else "M1_SUB"
            pars = (f'list(list("cutColumns" {len(cuts)}) list("cutSpacing" {point(cut_spacing,cut_spacing)}) '
                    f'list("layer1Enc" {enc}) list("layer2Enc" {enc}))')
            commands.append(f'lmlVia(cv tech "{vt}" {point(*center(rect))} {pars})')
            continue
        od = layers["diff"][0]
        gates = [placed([r[0], od[1], r[2], od[3]]) for r in layers["poly"]
                 if r[1] <= od[1] and r[3] >= od[3]]
        gate_xs = [center(r)[0] for r in gates]
        for j, line in enumerate(pc["devices"]):
            name = line.split()[1]
            (drain, gate, source, body), model, width = electrical[name]
            channel = gates[j]
            assert channel[3]-channel[1] == width and channel[2]-channel[0] == 30
            sd = [pins[f"SD_{j}"], pins[f"SD_{j+1}"]]
            source_rect, = [r for n,r in sd if n == source]
            gx = gate_xs[j]
            ori = "R0" if center(source_rect)[0] < gx else "MY"
            # Native one-finger PCells have their origin at the left gate edge.
            # Interior individual fingers share diffusion and have no intervening dummy.
            left_end, right_end = gx == min(gate_xs), gx == max(gate_xs)
            if ori == "MY":
                left_end, right_end = right_end, left_end
            flags = ["ON" if value else "OFF" for value in (left_end,right_end)]
            xy = [channel[0] if ori=="R0" else channel[2], channel[1]]
            commands += [f'mast=dbOpenCellViewByType("tsmcN28" "{model}" "layout" "" "r")',
                         f'inst=dbCreateParamInst(cv mast "{name}" {point(*xy)} "{ori}" 1 '
                         f'list(list("Wfg" "string" "{width}n") list("l" "string" "30n") '
                         f'list("leftDummyPoly" "string" "{flags[0]}") list("rightDummyPoly" "string" "{flags[1]}")))',
                         f'unless(inst && length(inst~>master~>terminals)==4 error("PCell evaluation {name}"))']
            for term, net in zip("DGSB", (drain,gate,source,body)):
                commands.append(f'lmlTerm(cv inst "{term}" "{net}")')
            gn, head = pins[f"G_{j+1}"]
            assert gn == gate
            ex, ey = ((head[2]-head[0]-40)//2, (head[3]-head[1]-40)//2)
            enc = point(ex, ey)
            commands.append(f'lmlVia(cv tech "M1_PO" {point(*center(head))} '
                            f'list(list("layer1Enc" {enc}) list("layer2Enc" {enc})))')
            inventory.append(dict(name=name, model=model, width_nm=width, length_nm=30,
                                  origin_nm=xy, orientation=ori, channel_nm=channel,
                                  connected=dict(zip("DGSB", (drain,gate,source,body)))))
    for sh in ast["shapes"]:
        layer = {"poly":"PO", "nwell":"NW"}[sh["layer"]]
        commands.append(f'lmlRect(cv "{layer}" {box(sh["box"])} nil)')
    for route in ast["routes"]:
        for path in route["paths"]:
            for rect in path["segRects"]:
                commands.append(f'lmlRect(cv "{METAL[path["layer"]]}" {box(rect)} "{route["net"]}")')
        for via in route["vias"]:
            assert via["rows"]==via["cols"]==1
            via_name = {1:"M2_M1", 2:"M3_M2"}[via["mBot"]]
            commands.append(f'lmlVia(cv tech "{via_name}" {point(via["vx"],via["vy"])} nil)')
    for pin in ast["cellPorts"]:
        name = pin["name"]
        direction = "input" if name in ("CLK","VINN","VINP") else "output" if name in ("OUTN","OUTP") else "inputOutput"
        commands.append(f'lmlPort(cv "{name}" {box(pin["box"])} {point(*pin["labelNm"])} "{direction}")')
    commands += ['unless(dbSave(cv) error("OA save failed"))', 'dbClose(cv)',
                 f'printf("LML_OA_SAVED {TOP}\\n") t))',
                 'if(errset(lmlBuild() t) then exit(0) else exit(1))']
    readback = ['procedure(lmlCheck() let((cv fp inst)',
                f'cv=dbOpenCellViewByType("{LIB}" "{TOP}" "layout" "" "r")',
                f'unless(cv && equal(cv~>lmlSourceSha256 "{metrics["lml_sha256"]}") error("source identity"))',
                'unless(length(cv~>instances)==11 && length(cv~>terminals)==7 error("native interface"))',
                'fp=outfile(strcat(getShellEnvVar("LML_RUN_PATH") "/readback.txt"))']
    for obj in inventory:
        name=obj["name"]
        readback += [f'inst=dbFindAnyInstByName(cv "{name}")',
                     f'unless(inst && equal(inst~>libName "tsmcN28") && equal(inst~>cellName "{obj["model"]}") '
                     f'&& equal(inst~>orient "{obj["orientation"]}") && equal(inst~>xy {point(*obj["origin_nm"])}) error("readback {name}"))',
                     f'unless(length(inst~>instTerms)==4 error("missing terminal {name}"))',
                     'foreach(it inst~>instTerms fprintf(fp "IT %s %s %s\\n" inst~>name it~>name it~>net~>name))',
                     'foreach(s inst~>master~>shapes when(equal(s~>purpose "error") error("PCell error marker")))',
                     'fprintf(fp "MOS %s %s %s %L\\n" inst~>name inst~>cellName inst~>orient inst~>xy)']
    readback += ['foreach(tn cv~>terminals foreach(p tn~>pins foreach(f p~>figs '
                 'fprintf(fp "PORT %s %s %L\\n" tn~>name f~>layerName f~>bBox))))',
                 'fprintf(fp "NATIVE_VIAS %d\\n" length(cv~>vias))',
                 'close(fp) dbClose(cv)',f'printf("LML_OA_READBACK {TOP}\\n") t))',
                 'if(errset(lmlCheck() t) then exit(0) else exit(1))']
    destination.mkdir(exist_ok=True, parents=True)
    files = {"build.il":"\n".join(commands)+"\n", "readback.il":"\n".join(readback)+"\n", "reference.cdl":cdl}
    metadata = dict(top=TOP, library=LIB, owned_predecessor=predecessor,
                    lml_sha256=metrics["lml_sha256"], electrical_sha256=metrics["netlist_sha256"],
                    files={n:hashlib.sha256(v.encode("ascii")).hexdigest() for n,v in files.items()})
    for n, value in files.items():
        (destination/n).write_bytes(value.encode("ascii"))
    for n, data in (("source.json",metadata), ("devices.json",inventory)):
        (destination/n).write_text(json.dumps(data, indent=2)+"\n", encoding="utf-8")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--layoutml", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--predecessor")
    args=p.parse_args()
    sys.path.insert(0, str(args.layoutml.resolve()/"explorations/Q-tech-decoupling"))
    import meso_compiler
    build(meso_compiler, args.out, args.predecessor)
