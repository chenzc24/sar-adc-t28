"""Prepare only the first reference reproduction circuit; no remote operations."""
from __future__ import annotations
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DEST = HERE / "generated/first_reproduction"
SOURCE = ROOT / "output/sar8_physical_repair/sar8fix-loaded-ref-ffcold"
EXPECTED = {"dut.scs": "a42e44613b4b1a8a74876a4c996f5bd2bf2e74bf13da6729818ab85bde5a21de",
            "test.scs": "e6160bb51a25fd41cec7a196da1bdbb9a701ec88f31de13a7d8bc8608d6ddcbf"}
TIMING_KEEP = {"X016", "X015", "X004", "X000", "X014", "X013", "X010", "X009",
               "X008", "X005", "X003", "X002", "X006", "XD_RAW_D", "X011", "XD_WRITE_D"}
TOP = "sar8_reference_isolation_v1"
GATES = [g+str(bit) for g in ["GNN","GNP","GPN","GPP"] for bit in range(8)]


def sha(value): return hashlib.sha256(value).hexdigest()
def dump(name, value): (DEST/name).write_text(json.dumps(value, indent=2)+"\n")


def definitions(text):
    found = list(re.finditer(r"(?ms)^subckt (\w+) .*?^ends \1\b", text))
    result = {m[1]:m[0] for m in found}
    if len(result) != len(found): raise ValueError("duplicate source master")
    return result


def statements(block):
    return [s.strip() for s in block.replace("\\\n"," ").splitlines()
            if s.strip() and not s.lstrip().startswith("//")]


def ports(block): return statements(block)[0].split()[2:]


def instances(block):
    for line in statements(block)[1:-1]:
        m = re.fullmatch(r"(\w+)\s+\(([^)]*)\)\s+(\w+)(.*)", line)
        if not m: raise ValueError("unsupported source statement "+line)
        yield m[1],m[2].split(),m[3],m[4].strip()


def emit(name, rows, pins):
    return "subckt "+name+" "+" ".join(pins)+"\n"+"\n".join(
        "    %s (%s) %s%s" % (n," ".join(ns),m,(" "+p) if p else "") for n,ns,m,p in rows)+"\nends "+name


def closure(defs, roots):
    seen=set()
    def visit(name):
        if name in seen:return
        seen.add(name)
        for _,_,model,_ in instances(defs[name]):
            if model in defs:visit(model)
    for root in roots:visit(root)
    return sorted(seen)


def flatten(defs, name, binding, prefix="XDUT"):
    result={}
    def walk(master, bind, scope):
        for n,args,model,p in instances(defs[master]):
            ns=[bind.get(a,a if a in ["0","VDD!"] else scope+"."+a) for a in args]
            full=scope+"."+n
            if model in defs:
                pins=ports(defs[model])
                if len(pins)!=len(ns):raise ValueError("port mismatch "+full)
                walk(model,dict(zip(pins,ns)),full)
            else:result[full]=dict(model=model,nodes=ns,parameters=" ".join(p.split()))
    walk(name,binding,prefix)
    return result


def logical_port(signal):
    return signal.replace("xdut.xref.","").replace("xdut.","").upper()


def replay_node(signal):return "REPLAY_"+signal.replace(".","_").replace("!","_").upper()


def canonical_node(node):
    node=node.replace(".XLOADCTRL.",".XCTRL.")
    node=re.sub(r"^XDUT.LOAD_D([0-7])$",r"D\1",node)
    node=re.sub(r"^XDUT.LOAD_CODE([0-7])$",r"XDUT.CODE\1",node)
    if node=="XDUT.LOAD_PHI_U":return "XDUT.PHI_U"
    if node=="XDUT.LOAD_ACTIVE":return "XDUT.ACTIVE"
    return node


def fanout(devices,node):
    return sorted((name,i+1,v["model"],sha(v["parameters"].encode()))
                  for name,v in devices.items() for i,n in enumerate(v["nodes"]) if n==node)


def build():
    DEST.mkdir(parents=True,exist_ok=True)
    for name,expected in EXPECTED.items():
        if sha((SOURCE/name).read_bytes())!=expected:raise ValueError("source SHA mismatch "+name)
    old=definitions((SOURCE/"dut.scs").read_text())
    defs=dict(old)
    cap_keep={"X008","X017","X018"}|{"XMUX%d"%b for b in range(8)}|{"XSTORE%d"%b for b in range(8)}
    cap_keep|={"XBBM%d"%b for b in range(8)}|{"XDRV%d"%b for b in range(8)}
    refpins=["CODE%d"%b for b in range(8)]+["D%d"%b for b in range(8)]+GATES
    refpins+=["PHI_U","CAP_REQ"]+["RST%d"%b for b in range(8)]+["VDD","VSS"]
    refrows=[x for x in instances(old["sar8i_refword"]) if x[0] in cap_keep]
    if {x[0] for x in refrows}!=cap_keep:raise ValueError("capture subset changed")
    defs["audit_ref_capture"]=emit("audit_ref_capture",refrows,refpins)
    timingrows=[x for x in instances(old["sar8p_timing"]) if x[0] in TIMING_KEEP]
    if {x[0] for x in timingrows}!=TIMING_KEEP:raise ValueError("receiver forward-cone changed")
    defs["audit_ref_load_timing"]=emit("audit_ref_load_timing",timingrows,
        ["CMP_CLK","COMP_N","COMP_P","DATA","PHI_U","PHI_W","SAMPLE","VDD","VSS"])
    ctrlpins=ports(old["sar8i_ctrl"])+["PHI_U_CMD"]
    ctrlrows=[]
    for n,args,model,p in instances(old["sar8i_ctrl"]):
        if n=="XTIM":
            ctrlrows.append((n,["CMP_CLK","COMP_N","COMP_P","DATA","PHI_U","PHI_W","SAMPLE","VDD","VSS"],"audit_ref_load_timing",""))
        elif n=="XSEQ":
            args[0]="PHI_U_CMD";ctrlrows.append((n,args,model,p))
        else:ctrlrows.append((n,args,model,p))
    defs["audit_ref_load_ctrl"]=emit("audit_ref_load_ctrl",ctrlrows,ctrlpins)
    from review_recovered_native import REPLAY
    inports=[logical_port(s) for s in REPLAY]
    if len(set(inports))!=len(inports):raise ValueError("ambiguous replay port")
    toppins=inports+["VDD!","VINN","VINP","VREFN","VREFP","VSS"]
    rows=[]
    for n,args,model,p in instances(old["sar_adc8_join_r4"]):
        if n in {"XBOOTN","XBOOTP","XCDAC","XCOMP","CL_COMP_N","CL_COMP_P","CL_CMP_CLK"}:
            rows.append((n,args,model,p))
    refargs=["CODE%d"%b for b in range(8)]+["D%d"%b for b in range(8)]+GATES
    refargs+=["PHI_U","CAP_REQ"]+["RST%d"%b for b in range(8)]+["VDD!","0"]
    rows.append(("XREF",refargs,"audit_ref_capture",""))
    ctrlargs=[]
    for pin in ports(old["sar8i_ctrl"]):
        if re.fullmatch(r"(CODE|D)[0-7]",pin):ctrlargs.append("LOAD_"+pin)
        elif pin=="PHI_U":ctrlargs.append("LOAD_PHI_U")
        elif pin=="SAMPLE":ctrlargs.append("SAMPLE_INT")
        elif pin=="VDD":ctrlargs.append("VDD!")
        elif pin=="VSS":ctrlargs.append("0")
        elif pin=="ACTIVE":ctrlargs.append("LOAD_ACTIVE")
        else:ctrlargs.append(pin)
    ctrlargs.append("PHI_U")
    rows.append(("XLOADCTRL",ctrlargs,"audit_ref_load_ctrl",""))
    test=(SOURCE/"test.scs").read_text().replace("\\\n"," ")
    for bit in range(8):
        m=re.search(r"(?m)^COUT%d \(([^)]*)\) (\w+) (.+)$"%bit,test)
        if not m:raise ValueError("missing original output load")
        rows.append(("COUT_LOAD%d"%bit,["LOAD_D%d"%bit,"0"],m[2],m[3]))
    defs[TOP]=emit(TOP,rows,toppins)
    selected=closure(defs,[TOP])
    if any(n in selected for n in ["sar_adc8_join_r4","sar8i_ctrl","sar8p_timing","sar8i_refword","sar8i_idle"]):
        raise ValueError("full ADC/async controller inadvertently retained")
    source_binding={p:p for p in ports(old["sar_adc8_join_r4"])}
    source_flat=flatten(old,"sar_adc8_join_r4",source_binding)
    binding={p:"XDUT."+p for p in toppins}
    for p in ["VDD!","VINN","VINP","VREFN","VREFP"]:binding[p]=p
    binding["VSS"]="0"
    for bit in range(8):
        binding["D%d"%bit]="D%d"%bit
        binding["RST%d"%bit]="XDUT.XREF.RST%d"%bit
    binding["CAP_REQ"]="XDUT.XREF.CAP_REQ"
    new_flat=flatten(defs,TOP,binding)
    canon={}
    for n,v in new_flat.items():
        name=n.replace(".XLOADCTRL.",".XCTRL.")
        canon[name]=dict(v,nodes=[canonical_node(x) for x in v["nodes"]])
    protected=["XDUT.COMP_P","XDUT.COMP_N","XDUT.XCTRL.XTIM.PR","XDUT.XCTRL.XTIM.NR",
               "XDUT.XCTRL.DATA","XDUT.XCTRL.PHI_W","XDUT.TOPP","XDUT.TOPN",
               "XDUT.XREF.XDRV0.GNNDRV","XDUT.GNN0","XDUT.XREF.Q0"]
    checks={}
    for node in protected:
        a,b=fanout(source_flat,node),fanout(canon,node)
        if a!=b:raise ValueError("changed protected fanout "+node)
        checks[node]=dict(equal=True,terminals=len(a))
    immutable=[n for n in source_flat if n.startswith(("XDUT.XBOOT","XDUT.XCOMP.","XDUT.XCDAC.","XDUT.XREF.XDRV","XDUT.XREF.XBBM","XDUT.XREF.XSTORE"))]
    for name in immutable:
        if source_flat[name]!=canon.get(name):raise ValueError("device/connection change "+name)
    wrapper_names={TOP,"audit_ref_capture","audit_ref_load_ctrl","audit_ref_load_timing"}
    native_hashes={n:sha(defs[n].encode()) for n in selected if n not in wrapper_names}
    (DEST/"dut.scs").write_text("// Local uncompiled reference reproduction fixture; no size optimization.\n"+
        "\n\n".join(defs[n] for n in selected)+"\n")
    tb_binding={logical_port(s):replay_node(s) for s in REPLAY}
    tb_binding.update({"VDD!":"VDD!","VINN":"VINN","VINP":"VINP","VREFN":"VREFN","VREFP":"VREFP","VSS":"0"})
    physical=flatten(defs,TOP,tb_binding)
    mos={n:v for n,v in physical.items() if v["model"].startswith(("nch_","pch_"))}
    saves={node for d in physical.values() for node in d["nodes"] if node!="0"}
    current_branches=set()
    for name,v in mos.items():
        if name.startswith("XDUT.XREF.XDRV0.") or name.startswith(("XDUT.XCDAC.XSN0.","XDUT.XCDAC.XSP0.")):
            current_branches.update(name+":"+str(i) for i in range(1,5))
        if name.startswith("XDUT.XCOMP.MNIN") or (name.startswith("XDUT.XBOOT") and ".Mmain" in name):
            current_branches.update(name+":"+str(i) for i in range(1,5))
    for name,v in physical.items():
        if name.startswith("XDUT.XREF.XDRV0.") and v["model"]=="rupolym":
            current_branches.update([name+":1",name+":2"])
        if name.startswith("XDUT.XCDAC.CMOM"):
            current_branches.update([name+":1",name+":2"])
    current_branches.update(x+":1" for x in ["VVDD","VREFHIGH","VREFLOW","RREFN","RREFP","CREFN","CREFP"])
    pair_records=[]
    for name,v in mos.items():
        if v["model"] in ["nch_mac","pch_mac"]:limit=.99
        elif v["model"] in ["nch_18_mac","pch_18_mac"]:limit=1.98
        else:raise ValueError("unknown device stress class "+v["model"])
        pins=dict(zip("dgsb",v["nodes"]))
        for a,b in ["ds","gs","gd","gb","bd","bs"]:
            pair_records.append(dict(instance=name,model=v["model"],terminal=a+b,
                                     nodes=[pins[a],pins[b]],screen_v=limit))
    kcl={}
    for node in ["XDUT.XREF.XDRV0.GNNDRV","XDUT.XREF.XDRV0.GNNB","XDUT.XREF.XDRV0.GNNA",
                 "XDUT.XREF.XDRV0.GNNRG","XDUT.GNN0"]:
        terms=[]
        for name,v in physical.items():
            for port,value in enumerate(v["nodes"],1):
                if value==node:
                    term=name+":"+str(port)
                    terms.append(term)
                    current_branches.add(term)
        if not terms:raise ValueError("KCL node missing "+node)
        kcl[node]=dict(sum_into_node_should_be_A=0,branches_positive_into_component=terms,
                       relation="Sum of component terminal currents on a node is zero; no extra multi factor")
    include_lines=[x for x in test.splitlines() if x.startswith("include ") and "dut.scs" not in x]
    ext_names=["VVINN","VVINP","VREFLOW","VREFHIGH","VVDD","RREFN","RREFP","RINN","RINP","CREFN","CREFP"]
    ext=[]
    for n in ext_names:
        found=re.findall(r"(?m)^"+n+r" .+$",test)
        if len(found)!=1:raise ValueError("external interface source mismatch "+n)
        ext+=found
    source_options=re.findall(r"(?m)^simulatorOptions options .+$",test)
    if len(source_options)!=1:raise ValueError("source options missing/duplicate")
    # Preserve numerical settings; only remove an obsolete output-file path.
    numerical_options=re.sub(r'\s+sensfile="[^"]*"',"",source_options[0])
    native_meta=json.loads((ROOT/"output/managed_execution/runs/sar8audit-ref-native-v1/collected/derived/native.meta.json").read_text())
    stop_s=native_meta["last_native_time_s"]
    deck=["// NOT READY FOR DISPATCH: full-native PWL packaging requires parent decision.",
          "simulator lang=spectre","global 0 VDD!","parameters SUP=0.99",*include_lines,
          'include "dut.scs"','include "boundary_sources_full_native.scs"',
          "XDUT ("+" ".join(tb_binding[p] for p in toppins)+") "+TOP,*ext,
          numerical_options,
          "saveOptions options save=selected currents=selected subcktiprobes=no useprobes=no",
          "tran_repro tran stop=%.17g maxstep=10p errpreset=conservative lteratio=10 strobeperiod=1n strobeoutput=all outputstart=0n"%stop_s]
    deck+=["save "+s for s in sorted(saves|current_branches)]
    (DEST/"test.scs").write_text("\n".join(deck)+"\n")
    dump("measurement_map.json",dict(current_sign="Positive into saved wrapper component terminal; current already includes multi",
        KCL=kcl,current_saves=sorted(current_branches),voltage_saves=sorted(saves),
        MOS_terminal_screens=pair_records,not_a_lifetime_signoff=True))
    moved=[dict(node=n,source_terminal_count=len(fanout(source_flat,n)),
                fixture_alias_terminal_count=len(fanout(canon,n)),
                removed=[x for x in fanout(source_flat,n) if x not in fanout(canon,n)])
           for n in ["XDUT.CMP_CLK","XDUT.PHI_U","XDUT.ACTIVE"]+["D%d"%b for b in range(8)]]
    dump("connection_audit.json",dict(source_hashes=EXPECTED,native_subcircuit_hashes=native_hashes,
        source_MOS=sum(v["model"].startswith(("nch_","pch_")) for v in source_flat.values()),
        fixture_MOS=len(mos),primitive_model_counts=dict(Counter(v["model"] for v in physical.values())),
        protected_immediate_terminal_fanouts=checks,unchanged_source_device_records=len(immutable),
        intentional_cuts=moved,physical_node_splits=[
            "Native replay D/CODE are reference capture inputs; readout-load D/CODE are separate physical nodes",
            "Readout-load PHI_U is observed only; original PHI_U replay clocks physical token bank/reference MUX",
            "COMP clock replay replaces original active clock/SR feedback; no retained active output is voltage-forced"],
        load_closure_limit="Immediate COMP/PR/NR/DATA/PHI_W fanout retained exactly; downstream cut states and missing D-to-reference feedback need electrical source-wave reproduction before acceptance",
        clock_generation_feedback_retained=False,whole_ADC_root_retained=False,simulator_compiled=False))
    dump("source_map.json",dict(source_dut=str((SOURCE/"dut.scs").relative_to(ROOT)),
        replay_port_binding=tb_binding,required_native_signals=REPLAY,
        source_to_fixture_instance_prefix={"XDUT.XCTRL":"XDUT.XLOADCTRL","all_other_retained_prefixes":"unchanged"},
        reference_capture_instances=sorted(cap_keep),receiver_forward_instances=sorted(TIMING_KEEP),
        top_level_ports=toppins,missing_package_file="boundary_sources_full_native.scs"))
    dump("recipe_suggestion.json",dict(status="proposal_only_not_a_managed_recipe",run_id=None,
        entry="test.scs",corner="FF/0.99V/-40C with TT passives",simulation_stop_s=stop_s,
        stop_reason="Last recovered native knot; no unobserved held-tail interval is simulated",
        proposed_resources=dict(threads=4,simulation_rss_mib=1024,analysis_rss_mib=256,max_output_mib=16384,collection_mib=32),
        required_before_dispatch=["Parent packaging choice for native PWL sources", "Review deliberate load/clock feedback cuts",
            "Approve numerical reproduction tolerances and KCL residual bounds","Freeze exact source hashes and source-map",
            "Prepare native current/KCL reducer as separate reviewed managed input"],
        proposed_reproduction_not_ADC_spec=dict(stage_peak_abs_agreement_v=.001,
            corresponding_halfrail_edge_agreement_ps=2,branch_KCL_abs_floor_a=1e-10,branch_KCL_relative_peak=1e-5,
            comment="Proposed diagnostic tolerances only; also require same node, transition, sign/order and correct reference command mapping"),
        remote_started=False))
    audit=json.loads((DEST/"connection_audit.json").read_text())
    print(json.dumps({k:audit[k] for k in ["source_MOS","fixture_MOS","unchanged_source_device_records"]},indent=2))
    print("LOCAL_CIRCUIT_PREPARED_PACKAGE_BLOCKED")


if __name__=="__main__":build()
